#!/usr/bin/env python3
"""Minimal, dependency-free release metadata check."""

from __future__ import annotations

from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from marmo_core import __version__  # noqa: E402


def main() -> int:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    version = re.search(r'^version = "([^"]+)"$', pyproject, flags=re.MULTILINE)
    if version is None or version.group(1) != __version__:
        raise SystemExit("pyproject.toml and marmo_core.__version__ must match")
    if not (ROOT / "README.md").is_file():
        raise SystemExit("README.md is required for packaging")
    changelog_path = ROOT / "CHANGELOG.md"
    if not changelog_path.is_file():
        raise SystemExit("CHANGELOG.md is required for packaging")
    changelog = changelog_path.read_text(encoding="utf-8")
    heading = rf"^## \[{re.escape(__version__)}\] - \d{{4}}-\d{{2}}-\d{{2}}$"
    if re.search(heading, changelog, flags=re.MULTILINE) is None:
        raise SystemExit(f"CHANGELOG.md must document version {__version__}")
    print(f"release check passed: {__version__}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
