"""Stamp every benchmark report with what produced it.

The experiment side installs marmo-core rather than vendoring it, so a result
file is only reproducible if it records which build, which inputs, and which
settings produced it. ``stamp`` always records the full commit SHA of the
checkout, whether tracked files were modified, and the interpreter and
benchmark-library versions. A runner adds what only it knows:

``dataset``
    ``{name: {"repo": ..., "revision": <40-hex commit>}}`` for every public
    dataset it read. A branch name such as ``main`` is refused: it moves.
``inputs``
    ``{name: sha256}`` for local files the numbers depend on (use
    :func:`sha256_file` and :func:`sha256_tree`).
``model``
    The models behind the numbers (embedding model, query prefix, ...).
``arguments``
    The settings of the run (an ``argparse.Namespace`` or a mapping).

Reports written before this schema have no ``provenance`` key and, for some
suites, no ``marmo_core_commit`` either; they are legacy and cannot be traced
to a build from the file alone.
"""

from __future__ import annotations

import hashlib
import platform
import re
import subprocess
from argparse import Namespace
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any, Mapping

PROVENANCE_SCHEMA = 2
_REVISION = re.compile(r"[0-9a-f]{40}")
_TRACKED_PACKAGES = ("numpy", "pyarrow", "fastembed", "usearch", "onnxruntime")
_RESULTS_PATHSPEC = ":(exclude)benchmarks/results"
_REPO_ROOT = Path(__file__).resolve().parent.parent


def _git(checkout: Path, *arguments: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(checkout), *arguments], capture_output=True, text=True, timeout=30
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() if completed.returncode == 0 else None


def _checkout() -> Path | None:
    """The git checkout the installed marmo-core package lives in, if any."""

    try:
        import marmo_core
    except ImportError:
        return None

    package_root = Path(marmo_core.__file__).resolve().parent
    for candidate in (package_root, *package_root.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _library_commit(checkout: Path | None = None) -> str | None:
    """Full 40-hex SHA of ``HEAD`` of the marmo-core checkout, if it is one."""

    checkout = checkout or _checkout()
    if checkout is None:
        return None
    revision = _git(checkout, "rev-parse", "HEAD")
    return revision if revision and _REVISION.fullmatch(revision) else None


def _library_dirty(checkout: Path | None = None) -> bool | None:
    """Whether tracked files outside ``benchmarks/results`` differ from ``HEAD``.

    Result files are excluded because the run being stamped rewrites them.
    Untracked files are not counted.
    """

    checkout = checkout or _checkout()
    if checkout is None:
        return None
    status = _git(checkout, "status", "--porcelain", "--untracked-files=no", "--", ".", _RESULTS_PATHSPEC)
    return None if status is None else bool(status)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_tree(root: Path) -> dict[str, str]:
    """``{path relative to root: sha256}`` of every file under ``root``, sorted."""

    return {
        path.relative_to(root).as_posix(): sha256_file(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _plain(value: Any) -> Any:
    """JSON-safe copy of ``value``; paths inside the repository stay relative."""

    if isinstance(value, Path):
        resolved = value.resolve()
        return resolved.relative_to(_REPO_ROOT).as_posix() if resolved.is_relative_to(_REPO_ROOT) else str(value)
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_plain(item) for item in value]
    return value


def _dependencies() -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in _TRACKED_PACKAGES:
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def _validated_dataset(dataset: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    recorded: dict[str, dict[str, Any]] = {}
    for name, entry in dataset.items():
        revision = entry.get("revision")
        if not isinstance(revision, str) or not _REVISION.fullmatch(revision):
            raise ValueError(
                f"dataset {name!r} needs a 40-hex commit revision, got {revision!r}: "
                "a branch or tag name moves, so the numbers could not be traced to the data"
            )
        recorded[name] = dict(entry)
    return recorded


def stamp(
    report: dict,
    *,
    dataset: Mapping[str, Mapping[str, Any]] | None = None,
    inputs: Mapping[str, str] | None = None,
    model: Mapping[str, Any] | None = None,
    arguments: Namespace | Mapping[str, Any] | None = None,
) -> dict:
    """Add provenance fields to ``report`` in place and return it."""

    try:
        import marmo_core

        version = marmo_core.__version__
    except ImportError:
        version = None

    checkout = _checkout()
    report["marmo_core_version"] = version
    report["marmo_core_commit"] = _library_commit(checkout)
    report["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    provenance: dict[str, Any] = {
        "schema": PROVENANCE_SCHEMA,
        "marmo_core_dirty": _library_dirty(checkout),
        "python": platform.python_version(),
        "dependencies": _dependencies(),
    }
    if dataset is not None:
        provenance["dataset"] = _validated_dataset(dataset)
    if inputs is not None:
        provenance["inputs"] = dict(inputs)
    if model is not None:
        provenance["model"] = _plain(model)
    if arguments is not None:
        provenance["arguments"] = _plain(vars(arguments) if isinstance(arguments, Namespace) else arguments)
    report["provenance"] = provenance
    return report
