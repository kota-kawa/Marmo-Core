"""Stamp every benchmark report with the marmo-core build it was produced by.

The experiment side installs marmo-core rather than vendoring it, so a result
file is only reproducible if it records which build produced it. Without this,
a report written before a routing change is indistinguishable from one written
after it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import subprocess


def _library_commit() -> str | None:
    """Short git revision of the installed marmo-core checkout, if it is one."""

    try:
        import marmo_core
    except ImportError:
        return None

    package_root = Path(marmo_core.__file__).resolve().parent
    for candidate in (package_root, *package_root.parents):
        if not (candidate / ".git").exists():
            continue
        try:
            completed = subprocess.run(
                ["git", "-C", str(candidate), "rev-parse", "--short", "HEAD"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if completed.returncode != 0:
            return None
        revision = completed.stdout.strip()
        return revision or None
    return None


def stamp(report: dict) -> dict:
    """Add provenance fields to ``report`` in place and return it."""

    try:
        import marmo_core

        version = marmo_core.__version__
    except ImportError:
        version = None

    report["marmo_core_version"] = version
    report["marmo_core_commit"] = _library_commit()
    report["generated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return report
