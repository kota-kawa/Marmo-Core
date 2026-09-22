#!/usr/bin/env python3
"""Verify that ``.env.example`` documents every environment variable the code reads.

``.env.example`` is the single source of truth for the variables Marmo-Core
reads at runtime. This check scans the library and the benchmark scripts for
literal environment lookups and fails when a variable is read but not
documented, or documented but no longer read.

Lookups are recognised in these forms::

    required_environment("OPENAI_MODEL")
    optional_environment("OPENAI_BASE_URL")
    required_positive_int_environment("ANTHROPIC_MAX_TOKENS")
    os.environ.get("OPENAI_API_KEY", "")
    os.environ["OPENAI_API_KEY"]
    os.getenv("OPENAI_API_KEY")

A variable whose name is built at runtime, such as
``f"MARMO_NOTIFICATION_{destination}_URL"``, is recognised when the f-string
starts with one of ``ENV_PREFIXES`` (so an unrelated ``f"HTTP_{code}"`` is not
mistaken for a variable), and is documented in ``.env.example`` as a commented
placeholder with the dynamic part in angle brackets::

    # MARMO_NOTIFICATION_<DESTINATION>_URL=

A commented-out ``# KEY=`` line counts as documented, which is what makes the
placeholder form work; a variable read through ``"KEY" in os.environ`` or
``os.environ.setdefault`` is not recognised.

Run it from anywhere:

    python3 scripts/check_env_documentation.py

The exit status is non-zero on a mismatch. The check is dependency-free.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE = ROOT / ".env.example"

# Code that runs for a library user or a benchmark operator. Developer-only
# helpers under tools/ (the skill collector) read their own variables and are
# documented in their module docstrings instead.
SOURCE_GLOBS: tuple[str, ...] = ("marmo_core/**/*.py", "benchmarks/*.py")

# Prefixes that identify a Marmo-Core environment variable when its name is
# assembled at runtime.
ENV_PREFIXES: tuple[str, ...] = ("MARMO_", "OPENAI_", "ANTHROPIC_", "BENCHMARK_")

_LOOKUP_RE = re.compile(
    r"(?:required_environment|optional_environment|required_positive_int_environment"
    r"|os\.environ\.get|os\.getenv)\(\s*[\"']([A-Z][A-Z0-9_]*)[\"']"
    r"|os\.environ\[\s*[\"']([A-Z][A-Z0-9_]*)[\"']\s*\]"
)
# f"MARMO_NOTIFICATION_{destination.upper()}_URL" -> MARMO_NOTIFICATION_<...>_URL
_DYNAMIC_RE = re.compile(r"f[\"']([A-Z][A-Z0-9_]*(?:\{[^}]*\}[A-Z0-9_]*)+)[\"']")
_DOCUMENTED_RE = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*(?:<[A-Z_]+>[A-Z0-9_]*)*)=", re.MULTILINE)
_WILDCARD = "<...>"


def _generalize(name: str) -> str:
    """Replace every dynamic segment (``{expr}`` or ``<NAME>``) with a wildcard."""

    return re.sub(r"\{[^}]*\}|<[A-Z_]+>", _WILDCARD, name)


def variables_read(source: str) -> set[str]:
    """Return the environment variable names a Python source reads literally."""

    names: set[str] = set()
    for match in _LOOKUP_RE.finditer(source):
        names.add(match.group(1) or match.group(2))
    for match in _DYNAMIC_RE.finditer(source):
        if match.group(1).startswith(ENV_PREFIXES):
            names.add(_generalize(match.group(1)))
    return names


def variables_documented(env_example: str) -> set[str]:
    """Return the variable names ``.env.example`` documents, placeholders generalized."""

    return {_generalize(match.group(1)) for match in _DOCUMENTED_RE.finditer(env_example)}


def compare(read: set[str], documented: set[str]) -> tuple[list[str], list[str]]:
    """Return ``(undocumented, unused)`` sorted lists."""

    return sorted(read - documented), sorted(documented - read)


def collect_sources(root: Path, patterns: Iterable[str] = SOURCE_GLOBS) -> list[Path]:
    sources: list[Path] = []
    for pattern in patterns:
        sources.extend(sorted(path for path in root.glob(pattern) if path.is_file()))
    return sources


def main() -> int:
    if not ENV_EXAMPLE.is_file():
        print(".env.example is missing", file=sys.stderr)
        return 1
    read: set[str] = set()
    for source in collect_sources(ROOT):
        read |= variables_read(source.read_text(encoding="utf-8"))
    documented = variables_documented(ENV_EXAMPLE.read_text(encoding="utf-8"))
    undocumented, unused = compare(read, documented)
    if undocumented:
        print("environment variables read by the code but missing from .env.example:", file=sys.stderr)
        for name in undocumented:
            print(f"  {name}", file=sys.stderr)
    if unused:
        print("environment variables documented in .env.example but never read:", file=sys.stderr)
        for name in unused:
            print(f"  {name}", file=sys.stderr)
    if undocumented or unused:
        return 1
    print(f"env documentation check passed: {len(documented)} variables")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
