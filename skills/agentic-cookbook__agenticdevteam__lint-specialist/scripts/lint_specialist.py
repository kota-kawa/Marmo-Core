#!/usr/bin/env python3
"""Specialist conformance linter for the v2.0.0 specs.

Validates a specialist DIRECTORY against the runtime loader contract
(`pipeline/engine/source/engine/conductor/team_loader.py`), as described by
`pipeline/engine/definitions/specialist-spec.md` and `specialty-team-spec.md`.

The loader is the source of truth, so this linter mirrors it exactly:
  - a specialist is the directory `specialists/<name>/`;
  - specialties are discovered by globbing `specialities/*.md` (British
    spelling; `specialties/` also accepted), skipping `index.md`;
  - frontmatter is parsed as flat `key: value` pairs only (no nested YAML),
    so `review_signals` MUST be a comma-separated string, not a block list;
  - a specialist with zero specialty files is silently DROPPED at load time
    — the linter raises that to a FAIL so it never ships unnoticed.

Severities:
  FAIL — breaks the review pipeline (specialist/specialty won't load or
         loads with empty review focus). Non-zero exit.
  WARN — hygiene / provenance drift (stale artifact path, missing persona).
         Reported, but does not fail the run.

Usage:
  lint_specialist.py <specialist-dir> [<specialist-dir> ...]
  lint_specialist.py --all <specialists-parent-dir>
  lint_specialist.py ... [--cookbook <cookbook-root>] [--quiet]

Exit 0 if no FAILs, 1 if any FAIL, 2 on bad invocation.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

KEBAB_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+([-+].*)?$")
KNOWN_TIERS = {"fast-cheap", "balanced", "high-reasoning"}
SPECIALTY_DIRS = ("specialities", "specialties")

# Default cookbook root for the optional artifact-existence check, anchored to
# this repo (scripts/ -> lint-specialist/ -> skills/ -> .claude/ -> repo root)
# so it resolves the same no matter the caller's cwd. Skipped entirely when
# absent. A cwd-relative default silently no-ops ST06b whenever the linter is
# run from anywhere but the repo root.
_REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_COOKBOOK = _REPO_ROOT / "external" / "agenticcookbook" / "cookbook"


@dataclass
class Finding:
    check: str          # e.g. "S02" / "ST04"
    severity: str       # "PASS" | "WARN" | "FAIL"
    target: str         # the file/dir the finding is about (repo-relative-ish)
    message: str


# ---------------------------------------------------------------------------
# Parsing — mirrors team_loader._parse_frontmatter / _extract_section exactly.
# ---------------------------------------------------------------------------


def _split_frontmatter(text: str) -> tuple[str | None, dict[str, str], str]:
    """Return (raw_header, flat_meta, body).

    raw_header is None when there is no well-formed `---`-delimited block
    (mirrors the loader treating the whole text as body). flat_meta only
    captures `key: value` lines, exactly like the runtime parser — block
    lists and nested maps are NOT represented.
    """
    if not text.startswith("---"):
        return None, {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return None, {}, text
    header = text[3:end].strip()
    body = text[end + 4:].lstrip("\n")
    meta: dict[str, str] = {}
    for line in header.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        meta[key.strip()] = val.strip()
    return header, meta, body


def _extract_section(markdown: str, heading: str) -> str:
    prefix = f"## {heading}"
    idx = markdown.find(prefix)
    if idx < 0:
        return ""
    start = idx + len(prefix)
    newline_after = markdown.find("\n", start)
    if newline_after < 0:
        return markdown[start:].strip()
    rest = markdown[newline_after + 1:]
    next_heading = rest.find("\n## ")
    section = rest if next_heading < 0 else rest[:next_heading]
    return section.strip()


# ---------------------------------------------------------------------------
# Specialty checks (ST-series) — one specialty .md file.
# ---------------------------------------------------------------------------


def _lint_specialty(
    md_path: Path, rel: str, raw_header: str | None,
    meta: dict[str, str], body: str,
) -> list[Finding]:
    """Lint one specialty from its already-parsed frontmatter.

    The caller reads and splits the file once and passes the parsed
    (raw_header, meta, body) here and to `_check_artifact_existence`, so the
    file is never read or parsed twice.
    """
    out: list[Finding] = []

    # ST01 — valid frontmatter delimiters.
    if raw_header is None:
        out.append(Finding("ST01", "FAIL", rel,
                            "missing or malformed `---` YAML frontmatter block"))
    else:
        out.append(Finding("ST01", "PASS", rel, "frontmatter delimiters present"))

    # ST02 — effective name (frontmatter `name` or filename stem) is kebab-case.
    eff_name = meta.get("name") or md_path.stem
    if KEBAB_RE.match(eff_name):
        out.append(Finding("ST02", "PASS", rel, f"name {eff_name!r} is kebab-case"))
    else:
        out.append(Finding("ST02", "FAIL", rel,
                            f"name {eff_name!r} is not kebab-case "
                            f"([a-z][a-z0-9]*(-[a-z0-9]+)*)"))

    # ST03 — logical_model (if present) is a known tier.
    if "logical_model" in meta:
        tier = meta["logical_model"]
        if tier in KNOWN_TIERS:
            out.append(Finding("ST03", "PASS", rel, f"logical_model {tier!r}"))
        else:
            out.append(Finding("ST03", "WARN", rel,
                               f"logical_model {tier!r} not in "
                               f"{sorted(KNOWN_TIERS)} — routing falls back to balanced"))

    # ST04 — Worker Focus present and non-empty (the reviewer's lens).
    if _extract_section(body, "Worker Focus"):
        out.append(Finding("ST04", "PASS", rel, "Worker Focus non-empty"))
    else:
        out.append(Finding("ST04", "FAIL", rel,
                            "`## Worker Focus` missing or empty — reviewer has no lens"))

    # ST05 — Verify present and non-empty (the verifier's criteria).
    if _extract_section(body, "Verify"):
        out.append(Finding("ST05", "PASS", rel, "Verify non-empty"))
    else:
        out.append(Finding("ST05", "FAIL", rel,
                            "`## Verify` missing or empty — verifier has no criteria"))

    # ST06 — artifact (if present) ends with .md; existence is a softer WARN.
    if "artifact" in meta:
        artifact = meta["artifact"]
        if not artifact.endswith(".md"):
            out.append(Finding("ST06", "WARN", rel,
                               f"artifact {artifact!r} does not end with .md"))
        else:
            out.append(Finding("ST06", "PASS", rel, f"artifact {artifact!r}"))

    # ST07 — version (if present) is valid semver.
    if "version" in meta:
        version = meta["version"]
        if SEMVER_RE.match(version):
            out.append(Finding("ST07", "PASS", rel, f"version {version}"))
        else:
            out.append(Finding("ST07", "WARN", rel,
                               f"version {version!r} is not valid semver"))

    return out


def _check_artifact_existence(
    rel: str, meta: dict[str, str], cookbook_root: Path
) -> Finding | None:
    """ST06b — artifact resolves under the cookbook root (provenance drift).

    Takes the already-parsed `meta` so the caller's single read is reused.
    """
    artifact = meta.get("artifact")
    if not artifact or not artifact.endswith(".md"):
        return None
    if (cookbook_root / artifact).is_file():
        return Finding("ST06b", "PASS", rel, f"artifact resolves: {artifact}")
    return Finding("ST06b", "WARN", rel,
                   f"artifact not found under {cookbook_root}/: {artifact} "
                   f"(provenance drift — cookbook moved/renamed?)")


# ---------------------------------------------------------------------------
# Specialist checks (S- / C-series) — one specialist directory.
# ---------------------------------------------------------------------------


def lint_specialist(
    specialist_dir: Path, cookbook_root: Path | None = None
) -> list[Finding]:
    """Lint a single specialist directory. Returns all findings (incl. PASS)."""
    out: list[Finding] = []
    rel = specialist_dir.name
    sp_md = specialist_dir / "specialist.md"

    # S01 — specialist.md exists with valid frontmatter.
    if not sp_md.is_file():
        out.append(Finding("S01", "FAIL", rel, "specialist.md is missing"))
        return out  # nothing else is meaningful without it
    text = sp_md.read_text(encoding="utf-8")
    raw_header, meta, body = _split_frontmatter(text)
    if raw_header is None:
        out.append(Finding("S01", "FAIL", rel,
                            "specialist.md has no `---` YAML frontmatter block"))
    else:
        out.append(Finding("S01", "PASS", rel, "specialist.md frontmatter present"))

    # S03 — review_signals (if present) is a comma-separated string of kebab
    # tokens. The flat parser cannot read a YAML block list, so an empty value
    # (block-list form) means the loader sees NO signals — a real footgun.
    # `effective_signals` is what the loader would actually route on.
    effective_signals: list[str] = []
    if "review_signals" in meta:
        raw = meta["review_signals"]
        if raw == "":
            out.append(Finding("S03", "FAIL", rel,
                               "review_signals is empty — a YAML block list is NOT "
                               "parsed by the loader; use `review_signals: a, b, c` "
                               "or omit the key entirely"))
        elif raw.startswith("["):
            out.append(Finding("S03", "FAIL", rel,
                               f"review_signals {raw!r} looks like inline-YAML; the "
                               f"loader splits on commas — use `a, b, c` (no brackets) "
                               f"or omit the key entirely"))
        else:
            tokens = [t.strip() for t in raw.split(",") if t.strip()]
            bad = [t for t in tokens if not KEBAB_RE.match(t)]
            if bad:
                out.append(Finding("S03", "FAIL", rel,
                                   f"review_signals has non-kebab tokens: {bad}"))
            else:
                effective_signals = tokens
                out.append(Finding("S03", "PASS", rel,
                                   f"review_signals: {tokens}"))

    # S04 — always_on (if present) coerces to a clear bool.
    always_on_true = False
    if "always_on" in meta:
        val = meta["always_on"].strip().lower()
        if val in ("true", "false", "yes", "no", "1", "0"):
            always_on_true = val in ("true", "yes", "1")
            out.append(Finding("S04", "PASS", rel, f"always_on={val}"))
        else:
            out.append(Finding("S04", "WARN", rel,
                               f"always_on {meta['always_on']!r} is ambiguous — "
                               f"loader treats only true/yes/1 as on"))

    # S06 — routability. A specialist with neither review_signals nor
    # always_on:true is never picked by the review selection prefilter. That is
    # valid ONLY for a specialist dispatched explicitly by name (e.g. the
    # report writer) — hence WARN, not FAIL. (S05 in the spec is the umbrella
    # "every specialty is valid", reported here per-specialty as ST01-ST07.)
    if not effective_signals and not always_on_true:
        out.append(Finding("S06", "WARN", rel,
                           "no review_signals and always_on is not true — never "
                           "signal-selected (OK only if dispatched explicitly by name)"))
    else:
        out.append(Finding("S06", "PASS", rel, "routable (signals or always_on)"))

    # S02 — specialities/ dir with >=1 non-index .md (else the specialist is
    # dropped at load time). Lint every specialty file found.
    spec_dir = None
    for candidate in SPECIALTY_DIRS:
        d = specialist_dir / candidate
        if d.is_dir():
            spec_dir = d
            break
    specialty_files: list[Path] = []
    if spec_dir is not None:
        specialty_files = sorted(
            p for p in spec_dir.iterdir()
            if p.suffix == ".md" and p.name != "index.md"
        )
    if not specialty_files:
        out.append(Finding("S02", "FAIL", rel,
                            "no specialities/*.md found — the loader DROPS a "
                            "specialist with zero specialties"))
    else:
        out.append(Finding("S02", "PASS", rel,
                            f"{len(specialty_files)} specialty file(s)"))
        for md in specialty_files:
            sp_rel = f"{rel}/{spec_dir.name}/{md.name}"
            # Read and parse each specialty file exactly once, then share the
            # parsed frontmatter with both the specialty checks and ST06b.
            sp_header, sp_meta, sp_body = _split_frontmatter(
                md.read_text(encoding="utf-8"))
            out.extend(_lint_specialty(md, sp_rel, sp_header, sp_meta, sp_body))
            if cookbook_root is not None:
                f = _check_artifact_existence(sp_rel, sp_meta, cookbook_root)
                if f is not None:
                    out.append(f)

    # C01 — title `# <Name> Specialist` (hygiene).
    first_line = body.strip().split("\n", 1)[0] if body.strip() else ""
    if first_line.startswith("# ") and first_line.rstrip().endswith(" Specialist"):
        out.append(Finding("C01", "PASS", rel, "title ends with ' Specialist'"))
    else:
        out.append(Finding("C01", "WARN", rel,
                           f"title should be `# <Name> Specialist`, got {first_line!r}"))

    # C02 — Role present and non-empty (hygiene).
    if _extract_section(body, "Role"):
        out.append(Finding("C02", "PASS", rel, "Role non-empty"))
    else:
        out.append(Finding("C02", "WARN", rel, "`## Role` missing or empty"))

    # C03 — Persona is not the `(coming)` placeholder (hygiene/transitional).
    persona = _extract_section(body, "Persona")
    if persona and persona.strip().lower() != "(coming)":
        out.append(Finding("C03", "PASS", rel, "Persona defined"))
    else:
        out.append(Finding("C03", "WARN", rel,
                           "Persona is the `(coming)` placeholder"))

    # C04 — Exploratory Prompts (if present) numbered and end with `?`.
    prompts = _extract_section(body, "Exploratory Prompts")
    if prompts:
        numbered = [ln.strip() for ln in prompts.splitlines()
                    if re.match(r"^\d+\.", ln.strip())]
        bad = [ln for ln in numbered if not ln.rstrip().endswith("?")]
        if numbered and not bad:
            out.append(Finding("C04", "PASS", rel,
                               f"{len(numbered)} exploratory prompt(s)"))
        elif bad:
            out.append(Finding("C04", "WARN", rel,
                               f"{len(bad)} exploratory prompt(s) do not end with '?'"))
        else:
            # Section present but nothing parses as a numbered prompt (e.g. a
            # bulleted or prose list) — would otherwise pass silently.
            out.append(Finding("C04", "WARN", rel,
                               "Exploratory Prompts present but has no numbered "
                               "prompts (use `1.`, `2.`, …)"))

    return out


# ---------------------------------------------------------------------------
# Reporting + CLI.
# ---------------------------------------------------------------------------


_ORDER = {"FAIL": 0, "WARN": 1, "PASS": 2}


def _report(findings: list[Finding], quiet: bool) -> tuple[int, int, int]:
    fails = sum(1 for f in findings if f.severity == "FAIL")
    warns = sum(1 for f in findings if f.severity == "WARN")
    passes = sum(1 for f in findings if f.severity == "PASS")
    shown = [f for f in findings if not (quiet and f.severity == "PASS")]
    for f in sorted(shown, key=lambda f: (_ORDER[f.severity], f.target, f.check)):
        print(f"{f.severity:4}  {f.check:5}  {f.target}: {f.message}")
    return fails, warns, passes


def _resolve_specialist_dirs(args: argparse.Namespace) -> list[Path]:
    if args.all:
        parent = Path(args.all)
        if not parent.is_dir():
            print(f"error: --all parent {parent} is not a directory", file=sys.stderr)
            raise SystemExit(2)
        return sorted(p for p in parent.iterdir() if p.is_dir())
    return [Path(p) for p in args.paths]


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", help="specialist directories to lint")
    parser.add_argument("--all", metavar="SPECIALISTS_DIR",
                        help="lint every immediate subdirectory of SPECIALISTS_DIR")
    parser.add_argument("--cookbook", metavar="ROOT",
                        help="cookbook root for artifact-existence checks "
                             f"(default: {DEFAULT_COOKBOOK} if it exists)")
    parser.add_argument("--quiet", action="store_true",
                        help="suppress PASS lines; show only WARN/FAIL")
    args = parser.parse_args(argv)

    if not args.paths and not args.all:
        parser.error("provide one or more specialist directories, or --all <dir>")

    cookbook_root: Path | None = None
    if args.cookbook:
        cookbook_root = Path(args.cookbook)
        if not cookbook_root.is_dir():
            print(f"error: --cookbook {cookbook_root} is not a directory",
                  file=sys.stderr)
            return 2
    elif DEFAULT_COOKBOOK.is_dir():
        cookbook_root = DEFAULT_COOKBOOK

    if cookbook_root is None:
        print(
            "note: no cookbook root found — artifact-existence (ST06b) checks "
            f"skipped. Pass --cookbook <root> or place it at {DEFAULT_COOKBOOK}.",
            file=sys.stderr,
        )

    targets = _resolve_specialist_dirs(args)
    if not targets:
        print("error: no specialist directories found", file=sys.stderr)
        return 2

    total_fail = 0
    for i, sp_dir in enumerate(targets):
        if not sp_dir.is_dir():
            print(f"FAIL  --     {sp_dir}: not a directory")
            total_fail += 1
            continue
        if i:
            print()
        print(f"# {sp_dir}")
        findings = lint_specialist(sp_dir, cookbook_root)
        fails, warns, passes = _report(findings, args.quiet)
        print(f"  -> {fails} FAIL  {warns} WARN  {passes} PASS")
        total_fail += fails

    print(f"\n{len(targets)} specialist(s) linted; {total_fail} FAIL total",
          file=sys.stderr)
    return 1 if total_fail else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
