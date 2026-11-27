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
``f"MARMO_NOTIFICATION_{destination}_URL"``, is recognised when that f-string
(or a local variable assigned from it) is the argument of one of the lookups
above and starts with one of ``ENV_PREFIXES``. The source is parsed with
``ast``, so a lookup in a comment or a docstring, or an f-string that is never
passed to a lookup (``f"HTTP_{code}"``, ``f"OPENAI_{x} failed"``), is not
counted. A variable is documented in ``.env.example`` as a commented
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

import ast
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

_LOOKUP_FUNCTIONS: frozenset[str] = frozenset(
    {"required_environment", "optional_environment", "required_positive_int_environment"}
)
_VARIABLE_NAME_RE = re.compile(r"[A-Z][A-Z0-9_]*")
_NAME_SEGMENT_RE = re.compile(r"[A-Z0-9_]*")
_DOCUMENTED_RE = re.compile(r"^\s*#?\s*([A-Z][A-Z0-9_]*(?:<[A-Z_]+>[A-Z0-9_]*)*)=", re.MULTILINE)
_WILDCARD = "<...>"


def _generalize(name: str) -> str:
    """Replace every ``<NAME>`` placeholder (or a leftover ``{expr}``) with a wildcard."""

    return re.sub(r"\{[^}]*\}|<[A-Z_]+>", _WILDCARD, name)


def _is_os_attribute(node: ast.expr, *names: str) -> bool:
    """Whether ``node`` is ``os.<names[0]>.<names[1]>...``."""

    for name in reversed(names):
        if not (isinstance(node, ast.Attribute) and node.attr == name):
            return False
        node = node.value
    return isinstance(node, ast.Name) and node.id == "os"


def _joined_name(node: ast.JoinedStr) -> str | None:
    """Return ``PREFIX_<...>_SUFFIX`` for an f-string shaped like a variable name, else None."""

    parts: list[str] = []
    dynamic = False
    for value in node.values:
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            if not _NAME_SEGMENT_RE.fullmatch(value.value):
                return None
            parts.append(value.value)
        else:
            dynamic = True
            parts.append(_WILDCARD)
    name = "".join(parts)
    if not dynamic or not name.startswith(ENV_PREFIXES):
        return None
    return name


class _LookupVisitor(ast.NodeVisitor):
    """Collect the names passed to environment lookups, following local string assignments."""

    def __init__(self) -> None:
        self.names: set[str] = set()
        self._scopes: list[dict[str, ast.expr]] = [{}]

    def _argument_name(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            for scope in reversed(self._scopes):
                if node.id in scope:
                    node = scope[node.id]
                    break
            else:
                return None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value if _VARIABLE_NAME_RE.fullmatch(node.value) else None
        if isinstance(node, ast.JoinedStr):
            return _joined_name(node)
        return None

    def _record(self, node: ast.expr) -> None:
        name = self._argument_name(node)
        if name is not None:
            self.names.add(name)

    def _remember(self, target: ast.expr, value: ast.expr | None) -> None:
        if isinstance(target, ast.Name):
            if isinstance(value, (ast.Constant, ast.JoinedStr)):
                self._scopes[-1][target.id] = value
            else:
                self._scopes[-1].pop(target.id, None)

    def _visit_scope(self, node: ast.AST) -> None:
        self._scopes.append({})
        self.generic_visit(node)
        self._scopes.pop()

    visit_FunctionDef = visit_AsyncFunctionDef = visit_Lambda = _visit_scope

    def visit_Assign(self, node: ast.Assign) -> None:
        self.generic_visit(node)
        for target in node.targets:
            self._remember(target, node.value)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self.generic_visit(node)
        self._remember(node.target, node.value)

    def visit_Call(self, node: ast.Call) -> None:
        function = node.func
        is_lookup = (isinstance(function, ast.Name) and function.id in _LOOKUP_FUNCTIONS) or (
            _is_os_attribute(function, "environ", "get") or _is_os_attribute(function, "getenv")
        )
        if is_lookup and node.args:
            self._record(node.args[0])
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if _is_os_attribute(node.value, "environ"):
            self._record(node.slice)
        self.generic_visit(node)


def variables_read(source: str) -> set[str]:
    """Return the environment variable names a Python source reads literally.

    Only code is considered: a comment, a docstring, or an f-string that is not
    the argument of a lookup does not count as a read.
    """

    visitor = _LookupVisitor()
    visitor.visit(ast.parse(source))
    return visitor.names


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
        try:
            read |= variables_read(source.read_text(encoding="utf-8"))
        except SyntaxError as error:
            print(f"cannot parse {source.relative_to(ROOT)}: {error}", file=sys.stderr)
            return 1
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
