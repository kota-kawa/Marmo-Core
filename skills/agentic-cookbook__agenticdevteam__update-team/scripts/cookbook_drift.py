#!/usr/bin/env python3
"""Detect drift between the cookbook submodule and the team's specialists.

Read-only analysis engine for the `update-team` skill. Given the cookbook SHA
the team was last reconciled against (the per-team marker
`cookbook-sync.json`) and the cookbook's current HEAD, it diffs the two,
collapses the cookbook's use-case duplication into logical changes, and
cross-references each change against the team data to answer four questions:

  Step 2  updated_guidelines      — referenced guidelines/principles that changed
  Step 3  specialists_to_update   — those changes rolled up to owning specialists
  Step 4  new_specialities_existing — new cookbook files in a covered domain
  Step 5  new_specialist_areas    — new cookbook files in an UNCOVERED domain
          stale_references        — referenced files that were deleted/renamed

It mutates nothing. The follow-on plan applies edits and advances the marker;
re-running this before that lands yields the same diff (idempotent).

The cookbook duplicates a cross-cutting guideline byte-for-byte (modulo its
`id:`/`domain:` frontmatter) into up to six use-case dirs
(`guidelines/{planning,implementing,testing,reviewing,shipping,cookbook}/...`).
Those per-copy ids are NOT stable logical keys, so we key on the path with its
use-case segment stripped — a restructure's 6x physical churn collapses to one
logical row. Ownership derives purely from specialty `artifact:` pointers (the
resolvable contract); a specialist's `## Cookbook Sources` prose is ignored
because it does not resolve and nothing keys off it.

Usage:
  cookbook_drift.py [--repo-root DIR] [--report-dir DIR] [--json]

Exit 0 on success (incl. up-to-date), non-zero if any team errors.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

# scripts/ -> update-team/ -> skills/ -> .claude/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[4]

# A first guidelines/ segment is a use-case (stripped when a domain dir follows
# it) only if it is one of these. A 2-level guideline whose dir IS a use-case is
# a use-case-direct file (no domain); the key records that kind so it can never
# collide with a domain that happens to share the name — `testing`/`reviewing`
# are both use-case dir names AND domain names in the cookbook.
USE_CASES = frozenset(
    {"planning", "implementing", "testing", "reviewing", "shipping", "cookbook"}
)

# Cookbook top-level dirs that make up the team's reference surface. compliance/
# is in scope (specialties ground to it, the manifest materializes it); the rest
# of the cookbook (recipes/, reference/, appendix/, ingredients/, ...) is not.
IN_SCOPE_TOPS = frozenset({"guidelines", "principles", "compliance"})


# ---------------------------------------------------------------------------
# Pure logic — directly unit-tested, no git or filesystem.
# ---------------------------------------------------------------------------


def logical_key(cookbook_rel: str) -> tuple[str, ...] | None:
    """Use-case-agnostic identity of a cookbook file, or None if out of scope.

    Cookbook-relative path (no `cookbook/` prefix) in, logical key out:
      guidelines/<uc>/<domain>/<rest...> -> ("guidelines", "domain",  <domain>, <rest>)
      guidelines/<domain>/<rest...>      -> ("guidelines", "domain",  <domain>, <rest>)
      guidelines/<uc>/<file>  (2-level)  -> ("guidelines", "usecase", <uc>,     <file>)
      principles/<rest...>                -> ("principles", <rest>)
      compliance/<rest...>                -> ("compliance", <rest>)

    The use-case segment is stripped only when a domain dir follows it, so the
    six use-case copies of one guideline share a single ("guidelines","domain",…)
    key. A 2-level file sitting directly under a use-case dir keeps a distinct
    ("guidelines","usecase",…) kind: without that token a domain named `testing`
    (under some use-case) and the `guidelines/testing/` use-case dir would
    collapse onto the same key — they are different files.
    """
    parts = [p for p in cookbook_rel.split("/") if p]
    if not parts:
        return None
    top = parts[0]
    if top == "guidelines":
        rest = parts[1:]
        if len(rest) >= 3 and rest[0] in USE_CASES:
            # <usecase>/<domain>/<rest...>: strip the use-case, keep the domain.
            return ("guidelines", "domain", rest[1], "/".join(rest[2:]))
        if len(rest) == 2:
            # 2-level: a use-case dir is use-case-direct; anything else a domain.
            kind = "usecase" if rest[0] in USE_CASES else "domain"
            return ("guidelines", kind, rest[0], rest[1])
        if len(rest) > 2:
            # 3+ levels not under a use-case: the first seg is the domain.
            return ("guidelines", "domain", rest[0], "/".join(rest[1:]))
        return None
    if top in ("principles", "compliance"):
        rest = parts[1:]
        if not rest:
            return None
        return (top, "/".join(rest))
    return None


def domain_group(key: tuple[str, ...]) -> tuple[str, ...]:
    """The ownership bucket a logical key belongs to, namespaced.

    Guidelines route by `(kind, group)` so a domain named `testing` and the
    `testing` use-case dir reach different owners; principles/compliance route
    by their single top segment.
    """
    if key[0] == "guidelines":
        return (key[1], key[2])   # (kind, group)
    return (key[0],)


def group_label(key: tuple[str, ...]) -> str:
    """A readable name for a logical key's ownership bucket (for the report)."""
    if key[0] == "guidelines":
        kind, group = key[1], key[2]
        return f"{group} (use-case)" if kind == "usecase" else group
    return key[0]


def fmt_key(key: tuple[str, ...]) -> str:
    """Render a logical key as a readable `a/b/c` path string (no kind token)."""
    if key[0] == "guidelines":
        # ("guidelines", kind, group, rest) -> "guidelines/<group>/<rest>"
        return "/".join(p for p in ("guidelines", key[2], key[3]) if p)
    return "/".join(p for p in key if p)


def _prefer_reviewing(paths: list[str]) -> str:
    """Deterministically pick a representative copy — review-team relevance first."""
    review = sorted(p for p in paths if "/reviewing/" in f"/{p}")
    return review[0] if review else sorted(paths)[0]


@dataclass
class Change:
    """One physical diff entry, paths cookbook-relative."""
    status: str          # "A" | "M" | "D" | "R"
    path: str            # added/modified/deleted path, or the OLD path of a rename
    new_path: str | None = None  # rename destination


def parse_name_status(diff_text: str, prefix: str) -> tuple[list[Change], int]:
    """Parse `git diff --name-status -M` output into in-scope Changes.

    Only paths under `prefix` (the cookbook content root within the submodule,
    e.g. `cookbook`) and one of IN_SCOPE_TOPS are kept; the rest are counted and
    returned as `dropped` so the caller can warn without silently truncating.
    """
    pre = prefix.rstrip("/") + "/" if prefix else ""

    def to_rel(p: str) -> str | None:
        if pre and not p.startswith(pre):
            return None
        rel = p[len(pre):]
        return rel if rel.split("/", 1)[0] in IN_SCOPE_TOPS else None

    changes: list[Change] = []
    dropped = 0
    for line in diff_text.splitlines():
        if not line.strip():
            continue
        cols = line.split("\t")
        code = cols[0].strip()
        letter = code[0]
        if letter in ("R", "C") and len(cols) >= 3:
            old, new = to_rel(cols[1]), to_rel(cols[2])
            if letter == "C":
                # a copy leaves the source intact; only the destination is new.
                if new is not None:
                    changes.append(Change("A", new))
                continue
            if old is None and new is None:
                continue  # both out of scope — not cookbook content at all
            if old is None or new is None:
                # rename crosses the scope boundary; treat the in-scope half.
                if old is not None:
                    changes.append(Change("D", old))
                if new is not None:
                    changes.append(Change("A", new))
                continue
            changes.append(Change("R", old, new))
        elif letter == "T" and len(cols) >= 2:
            rel = to_rel(cols[1])          # typechange ~ a content modification
            if rel is None:
                dropped += 1
                continue
            changes.append(Change("M", rel))
        elif letter in ("A", "M", "D") and len(cols) >= 2:
            rel = to_rel(cols[1])
            if rel is None:
                dropped += 1
                continue
            changes.append(Change(letter, rel))
        else:
            # U (unmerged), X/B (unknown/broken), or a malformed line — never
            # expected for plain markdown; count so nothing is silently lost.
            dropped += 1
    return changes, dropped


@dataclass
class Grounded:
    """A grounded specialty: its rel id, owning specialist, and cookbook artifact.

    `specialty_rel` is specialist-first (`<specialist>/<area>/<name>.md` in the
    area-pool layout, `<specialist>/specialities/<x>.md` in the legacy nested
    one) so the step-3 rollup can recover the owning specialist with a single
    `split("/", 1)`."""
    specialty_rel: str
    specialist: str
    artifact: str        # cookbook-relative


def build_report(
    changes: list[Change],
    current_paths: set[str],
    grounded: list[Grounded],
    manifest_srcs: list[str],
) -> dict:
    """Categorize changes against the team data. Pure — no git, no fs.

    Returns the per-team buckets + summary (everything below `status`).
    """
    # Indexes off the grounded specialties (artifact: is the only ownership key).
    art_logical: dict[tuple, list[Grounded]] = defaultdict(list)
    ownership: dict[tuple, set[str]] = defaultdict(set)
    for g in grounded:
        k = logical_key(g.artifact)
        if k is None:
            continue
        art_logical[k].append(g)
        ownership[domain_group(k)].add(g.specialist)
    src_logical: dict[tuple, list[str]] = defaultdict(list)
    for src in manifest_srcs:
        k = logical_key(src)
        if k is not None:
            src_logical[k].append(src)
    src_set = set(manifest_srcs)

    # Fold physical entries into per-logical-key status sets + path sets.
    added, modified = set(), set()
    removed: dict[str, str] = {}      # old path -> "D" | "R"
    rename_new: dict[str, str] = {}   # old path -> new path
    for c in changes:
        if c.status == "A":
            added.add(c.path)
        elif c.status == "M":
            modified.add(c.path)
        elif c.status == "D":
            removed[c.path] = "D"
        elif c.status == "R":
            removed[c.path] = "R"
            rename_new[c.path] = c.new_path or ""

    status_of: dict[tuple, set[str]] = defaultdict(set)
    phys_of: dict[tuple, set[str]] = defaultdict(set)
    for grp, letter in ((added, "A"), (modified, "M"), (set(removed), "D")):
        for p in grp:
            k = logical_key(p)
            if k is not None:
                status_of[k].add(letter)
                phys_of[k].add(p)

    # --- Step 2: referenced guidelines/principles that changed ---------------
    updated: list[dict] = []
    for k, st in status_of.items():
        is_modified = ("M" in st) or ({"A", "D"} <= st)
        if not is_modified:
            continue
        ref_art = art_logical.get(k, [])
        ref_src = sorted(src_logical.get(k, []))
        if not ref_art and not ref_src:
            continue  # changed but nothing references it — not actionable
        phys = sorted(phys_of[k])
        updated.append({
            "logical_key": fmt_key(k),
            "domain_group": group_label(k),
            "change": "MODIFIED",
            "physical_count": len(phys),
            "physical_paths": phys,
            "referenced_by_artifact": sorted(g.specialty_rel for g in ref_art),
            "referenced_by_manifest_src": ref_src,
            "owners": sorted({g.specialist for g in ref_art}),
            "materialized_but_unowned": not ref_art and bool(ref_src),
        })
    updated.sort(key=lambda e: e["logical_key"])

    # --- Step 3: roll step-2 hits up to owning specialists -------------------
    rollup: dict[str, dict] = defaultdict(
        lambda: {"logical_keys": set(), "specialities": set()})
    for u in updated:
        for sp_rel in u["referenced_by_artifact"]:
            name = sp_rel.split("/", 1)[0]
            rollup[name]["logical_keys"].add(u["logical_key"])
            rollup[name]["specialities"].add(sp_rel)
    specialists_to_update = [
        {"specialist": name,
         "logical_keys": sorted(v["logical_keys"]),
         "specialities_affected": sorted(v["specialities"])}
        for name, v in sorted(rollup.items())
    ]

    # --- Steps 4 & 5: new guidelines (a new copy appeared) -------------------
    new_existing, new_areas = [], []
    for k, st in status_of.items():
        if "A" not in st:
            continue            # no new copy appeared
        if k in art_logical:
            continue            # a new copy of an already-grounded guideline
        if k in src_logical:
            continue            # already materialized by the manifest
        dg = domain_group(k)
        owners = sorted(ownership.get(dg, set()))
        phys = sorted(phys_of[k])
        entry = {
            "logical_key": fmt_key(k),
            "domain_group": group_label(k),
            # pure A is a clean addition; A mixed with M/D means a new copy
            # landed alongside an edit/removal elsewhere — still surface it.
            "change": "ADDED" if st == {"A"} else "ADDED+MODIFIED",
            "physical_count": len(phys),
            "physical_paths": phys,
            "owners": owners,
        }
        (new_existing if owners else new_areas).append(entry)
    new_existing.sort(key=lambda e: e["logical_key"])
    new_areas.sort(key=lambda e: e["logical_key"])

    # --- Stale references: deleted/renamed paths that are still referenced ----
    def suggest(path: str) -> tuple[str | None, str]:
        if path in rename_new and rename_new[path]:
            return rename_new[path], "RENAMED"
        k = logical_key(path)
        survivors = (
            [c for c in current_paths if logical_key(c) == k]
            if k is not None else []
        )
        if survivors:
            return _prefer_reviewing(survivors), "MOVED"
        base = path.rsplit("/", 1)[-1]
        cands = [a for a in added if a.rsplit("/", 1)[-1] == base]
        if cands:
            return _prefer_reviewing(cands), "RENAMED?"
        return None, "DELETED"

    stale: list[dict] = []
    for path in sorted(removed):
        broken_art = sorted(g.specialty_rel for g in grounded if g.artifact == path)
        broken_src = [path] if path in src_set else []
        if not broken_art and not broken_src:
            continue            # an unreferenced copy was removed — no impact
        suggested, change = suggest(path)
        stale.append({
            "logical_key": fmt_key(logical_key(path) or (path,)),
            "change": change,
            "old_path": path,
            "suggested_new_artifact": suggested,
            "broken_artifacts": broken_art,
            "broken_manifest_srcs": broken_src,
        })
    stale.sort(key=lambda e: e["old_path"])

    summary = {
        "updated_referenced": len(updated),
        "specialists_to_update": len(specialists_to_update),
        "new_specialities_existing": len(new_existing),
        "new_specialist_areas": len(new_areas),
        "stale_references": len(stale),
    }
    return {
        "summary": summary,
        "updated_guidelines": updated,
        "specialists_to_update": specialists_to_update,
        "new_specialities_existing": new_existing,
        "new_specialist_areas": new_areas,
        "stale_references": stale,
    }


# ---------------------------------------------------------------------------
# Git + filesystem layer — gathers inputs, then calls the pure build_report.
# ---------------------------------------------------------------------------


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd),
        capture_output=True, text=True,
    )


def _git_ok(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    """Like _git but raises on a non-zero exit, so a silent git failure can't
    masquerade as an empty result (fail-fast). _safe_analyze turns the
    RuntimeError into a per-team error rather than aborting the whole run."""
    res = _git(cwd, *args)
    if res.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed in {cwd}: {res.stderr.strip()}")
    return res


def _artifact_of(md_text: str) -> str | None:
    """The `artifact:` value from a specialty's frontmatter, or None.

    A tolerant whole-file scan that mirrors the devteam reference-integrity
    test's `_artifact_of` exactly, so the engine grounds precisely what the green
    gate grounds. A frontmatter-fence parser would miss the pointer in a slightly
    malformed specialty (no closing `---`) that the test still grounds, making
    engine ownership silently disagree with the contract it is checked against.
    """
    for line in md_text.splitlines():
        s = line.strip()
        if s == "---":
            continue
        if s.startswith("artifact:"):
            return line.partition(":")[2].strip()
    return None


def _specialities_refs(md_text: str) -> list[str]:
    """The qualified ids from a specialist.md `specialities:`/`specialties:`
    frontmatter list (comma-separated `area/name`). A tolerant whole-file scan,
    matching `_artifact_of`'s robustness against a malformed fence."""
    for line in md_text.splitlines():
        s = line.strip()
        for key in ("specialities:", "specialties:"):
            if s.startswith(key):
                return [r.strip() for r in s[len(key):].split(",") if r.strip()]
    return []


def _collect_grounded(team_dir: Path) -> list[Grounded]:
    """Grounded specialties for a team.

    Current spec — a shared area pool `specialities/<area>/<name>.md` (each with
    an `artifact:` pointer) referenced from each `specialist.md` by qualified id
    `area/name`; the reference IS the ownership. One Grounded per (referencing
    specialist, specialty), so a changed guideline rolls up to every specialist
    that references the specialty grounding to it. Falls back to the legacy
    nested layout (`specialists/<n>/specialities/<x>.md`) for an un-migrated team.
    """
    # The area pool: qualified id `area/name` -> cookbook artifact.
    pool: dict[str, str] = {}
    for spelling in ("specialities", "specialties"):
        for md in sorted((team_dir / spelling).glob("*/*.md")):
            if md.name == "index.md":
                continue
            artifact = _artifact_of(md.read_text(encoding="utf-8"))
            if artifact:
                pool[f"{md.parent.name}/{md.stem}"] = artifact

    out: list[Grounded] = []
    if pool:
        for sp_md in sorted(team_dir.glob("specialists/*/specialist.md")):
            specialist = sp_md.parent.name
            for qid in _specialities_refs(sp_md.read_text(encoding="utf-8")):
                artifact = pool.get(qid)
                if artifact:
                    # Specialist-first rel so the step-3 rollup's split() works.
                    out.append(Grounded(f"{specialist}/{qid}.md", specialist, artifact))
        return out

    # Legacy nested layout fallback (pre-area-pool teams).
    for spelling in ("specialities", "specialties"):
        for md in sorted(team_dir.glob(f"specialists/*/{spelling}/*.md")):
            if md.name == "index.md":
                continue
            artifact = _artifact_of(md.read_text(encoding="utf-8"))
            if not artifact:
                continue
            specialist = md.parent.parent.name
            out.append(Grounded(f"{specialist}/{spelling}/{md.name}", specialist, artifact))
    return out


def _current_cookbook_paths(submodule: Path, sha: str, prefix: str) -> set[str]:
    """All in-scope cookbook-relative file paths present at `sha`."""
    res = _git_ok(submodule, "ls-tree", "-r", "--name-only", sha)
    pre = prefix.rstrip("/") + "/" if prefix else ""
    out: set[str] = set()
    for p in res.stdout.splitlines():
        if pre and not p.startswith(pre):
            continue
        rel = p[len(pre):]
        if rel.split("/", 1)[0] in IN_SCOPE_TOPS:
            out.add(rel)
    return out


def _bootstrap_sha(repo_root: Path, submodule_relpath: str) -> str | None:
    """The cookbook gitlink recorded on origin/main (first-run baseline).

    Deliberately does NOT fall back to local HEAD: after Step 1 bumps the
    gitlink, HEAD's gitlink == new_sha, so bootstrapping from it would report a
    spurious 'up-to-date' and mask real drift (fail-fast over a wrong answer).
    """
    for ref in ("origin/main", "origin/master"):
        res = _git(repo_root, "ls-tree", ref, "--", submodule_relpath)
        # format: "160000 commit <sha>\t<path>"
        for line in res.stdout.splitlines():
            fields = line.split()
            if len(fields) >= 3 and fields[1] == "commit":
                return fields[2]
    return None


def analyze_team(manifest_path: Path, repo_root: Path) -> dict:
    """Gather git/fs inputs for one grounded team and categorize the drift."""
    team_dir = manifest_path.parent
    name = team_dir.name
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    source_root = (repo_root / manifest["source_root"]).resolve()
    base = {
        "name": name,
        "source_root": manifest["source_root"],
        "warnings": [],
    }

    if not source_root.is_dir():
        return {**base, "status": "error",
                "warnings": [f"cookbook source not checked out at {manifest['source_root']}"]}

    top = _git(source_root, "rev-parse", "--show-toplevel")
    if top.returncode != 0:
        return {**base, "status": "error",
                "warnings": ["cookbook source_root is not inside a git submodule"]}
    submodule = Path(top.stdout.strip())
    prefix = str(source_root.relative_to(submodule))
    submodule_relpath = str(submodule.relative_to(repo_root))

    new_sha = _git_ok(submodule, "rev-parse", "HEAD").stdout.strip()

    marker_path = team_dir / "cookbook-sync.json"
    old_sha, baseline_source = "", "marker"
    if marker_path.is_file():
        try:
            marker = json.loads(marker_path.read_text(encoding="utf-8"))
            old_sha = marker.get("synced_sha", "")
        except (json.JSONDecodeError, AttributeError) as e:
            base["warnings"].append(
                f"cookbook-sync.json is malformed ({e!r}) — falling back to the "
                "origin/main gitlink baseline.")
    if not old_sha:
        # An absent, empty, or malformed marker all bootstrap the same way.
        old_sha = _bootstrap_sha(repo_root, submodule_relpath) or ""
        baseline_source = "bootstrap-gitlink"
        base["warnings"].append(
            "no usable cookbook-sync.json marker — baseline seeded from the "
            "origin/main gitlink; the follow-on plan must create the marker at "
            "new_sha.")

    base.update({"old_sha": old_sha, "new_sha": new_sha,
                 "baseline_source": baseline_source})

    if not old_sha:
        return {**base, "status": "error",
                "warnings": base["warnings"] + [
                    "could not determine a baseline cookbook SHA — no usable "
                    "cookbook-sync.json marker and the origin/main gitlink could "
                    "not be resolved; ensure the superproject has an 'origin' "
                    "remote and run `git fetch origin`."]}
    if _git(submodule, "cat-file", "-e", f"{old_sha}^{{commit}}").returncode != 0:
        _git(submodule, "fetch")
        if _git(submodule, "cat-file", "-e", f"{old_sha}^{{commit}}").returncode != 0:
            return {**base, "status": "error",
                    "warnings": base["warnings"] + [
                        f"baseline sha {old_sha[:12]} unknown to the submodule even "
                        f"after fetch — run `git -C {submodule_relpath} fetch`"]}
    if old_sha == new_sha:
        return {**base, "status": "up-to-date",
                "summary": {}, "updated_guidelines": [], "specialists_to_update": [],
                "new_specialities_existing": [], "new_specialist_areas": [],
                "stale_references": []}

    diff = _git(submodule, "diff", "--name-status", "-M", old_sha, new_sha)
    if diff.returncode != 0:
        return {**base, "status": "error",
                "warnings": base["warnings"] + [f"git diff failed: {diff.stderr.strip()}"]}

    changes, dropped = parse_name_status(diff.stdout, prefix)
    if dropped:
        base["warnings"].append(
            f"{dropped} changed file(s) outside guidelines/principles/compliance "
            f"were ignored (out of the team's reference surface)")

    grounded = _collect_grounded(team_dir)
    manifest_srcs = [f["src"] for f in manifest.get("files", [])]
    current = _current_cookbook_paths(submodule, new_sha, prefix)

    report = build_report(changes, current, grounded, manifest_srcs)
    has_drift = any(report["summary"].values())
    return {**base, "status": "drift-detected" if has_drift else "up-to-date", **report}


def _safe_analyze(manifest_path: Path, repo_root: Path) -> dict:
    """analyze_team with a last-resort guard: an unexpected error in one team
    (e.g. a git/_git_ok failure) becomes that team's error result instead of
    aborting the whole run."""
    name = manifest_path.parent.name
    try:
        return analyze_team(manifest_path, repo_root)
    except Exception as e:   # noqa: BLE001 — deliberate per-team isolation
        return {"name": name, "source_root": "", "status": "error",
                "warnings": [f"unexpected error analyzing team: {e!r}"]}


# ---------------------------------------------------------------------------
# Markdown rendering.
# ---------------------------------------------------------------------------


def _link(source_root: str, cookbook_rel: str) -> str:
    return f"`{source_root}/{cookbook_rel}`"


def render_markdown(result: dict) -> str:
    sr = result.get("source_root", "")
    L: list[str] = []
    L.append(f"## Team: `{result['name']}`")
    L.append("")
    L.append(f"- **Status:** {result['status']}")
    if "old_sha" in result:
        L.append(f"- **Baseline → HEAD:** `{result['old_sha'][:12]}` → "
                 f"`{result['new_sha'][:12]}`  ({result.get('baseline_source','')})")
    for w in result.get("warnings", []):
        L.append(f"- ⚠️ {w}")
    L.append("")

    if result["status"] == "error":
        L.append("> Analysis could not complete — see warnings above.")
        L.append("")
        return "\n".join(L)
    if result["status"] == "up-to-date":
        L.append("> Already in sync — no cookbook changes since the last reconcile.")
        L.append("")
        return "\n".join(L)

    s = result["summary"]
    L.append("| Bucket | Count |")
    L.append("| --- | --- |")
    L.append(f"| Updated referenced guidelines (step 2) | {s['updated_referenced']} |")
    L.append(f"| Specialists to update (step 3) | {s['specialists_to_update']} |")
    L.append(f"| New specialities for existing specialists (step 4) | {s['new_specialities_existing']} |")
    L.append(f"| New specialist areas (step 5) | {s['new_specialist_areas']} |")
    L.append(f"| Stale references to fix | {s['stale_references']} |")
    L.append("")

    if result["stale_references"]:
        L.append("### Stale references — fix first (broken `artifact:` / manifest `src`)")
        L.append("")
        for e in result["stale_references"]:
            sug = (_link(sr, e["suggested_new_artifact"])
                   if e["suggested_new_artifact"] else "_none found — investigate_")
            L.append(f"- **{e['change']}** {_link(sr, e['old_path'])} → {sug}")
            if e["broken_artifacts"]:
                L.append(f"  - breaks artifacts: {', '.join('`'+b+'`' for b in e['broken_artifacts'])}")
            if e["broken_manifest_srcs"]:
                L.append(f"  - breaks manifest src(s): {', '.join('`'+b+'`' for b in e['broken_manifest_srcs'])}")
        L.append("")

    if result["specialists_to_update"]:
        L.append("### Step 3 — specialists whose grounding changed")
        L.append("")
        for e in result["specialists_to_update"]:
            L.append(f"- **`{e['specialist']}`** — {len(e['specialities_affected'])} "
                     f"speciality(ies): {', '.join('`'+x+'`' for x in e['specialities_affected'])}")
        L.append("")

    if result["updated_guidelines"]:
        L.append("### Step 2 — updated guidelines/principles (referenced)")
        L.append("")
        for e in result["updated_guidelines"]:
            tag = " _(materialized but unowned — prunable?)_" if e["materialized_but_unowned"] else ""
            copies = f" ({e['physical_count']} copies)" if e["physical_count"] > 1 else ""
            L.append(f"- `{e['logical_key']}`{copies}{tag} — owners: "
                     f"{', '.join('`'+o+'`' for o in e['owners']) or '—'}")
        L.append("")

    if result["new_specialities_existing"]:
        L.append("### Step 4 — new guidelines in covered domains (add as specialities)")
        L.append("")
        for e in result["new_specialities_existing"]:
            L.append(f"- `{e['logical_key']}` — candidate owner(s): "
                     f"{', '.join('`'+o+'`' for o in e['owners'])}")
        L.append("")

    if result["new_specialist_areas"]:
        L.append("### Step 5 — new guidelines in UNCOVERED domains (new specialist?)")
        L.append("")
        for e in result["new_specialist_areas"]:
            L.append(f"- `{e['logical_key']}` — domain `{e['domain_group']}` has no specialist")
        L.append("")

    return "\n".join(L)


def render_document(new_sha: str, results: list[dict]) -> str:
    L = [f"# Cookbook drift report — `{new_sha[:12]}`", ""]
    L.append("Generated by the `update-team` skill (read-only analysis). Use this as "
             "the input to the team-update plan. **The plan's final step must write "
             "each team's `cookbook-sync.json` `synced_sha` to the new HEAD and "
             "re-run the linter + integrity tests.**")
    L.append("")
    for r in results:
        L.append(render_markdown(r))
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------
# CLI.
# ---------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo-root", default=str(_REPO_ROOT),
                    help="repo root (default: anchored to this script)")
    ap.add_argument("--report-dir", default=None,
                    help="where to write the markdown report (default: <repo>/docs/planning)")
    ap.add_argument("--json", action="store_true",
                    help="print the full JSON analysis to stdout instead of writing a report")
    args = ap.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    teams_dir = repo_root / "teams"
    manifests = sorted(teams_dir.rglob("reference-manifest.json"))
    if not manifests:
        print(f"error: no reference-manifest.json found under {teams_dir}", file=sys.stderr)
        return 2

    results = [_safe_analyze(m, repo_root) for m in manifests]
    new_sha = next((r["new_sha"] for r in results if r.get("new_sha")), "unknown")
    errored = any(r["status"] == "error" for r in results)
    has_drift = any(r["status"] == "drift-detected" for r in results)

    if args.json:
        print(json.dumps({"schema_version": 2, "new_sha": new_sha, "teams": results},
                         indent=2))
        return 1 if errored else 0

    # Only write a report when there is drift to plan. With no drift there is
    # nothing for the follow-on plan to consume, and new_sha may be "unknown"
    # (every team errored) — writing then would leave a stray
    # cookbook-drift-unknown.md.
    if has_drift:
        report_dir = (Path(args.report_dir) if args.report_dir
                      else repo_root / "docs" / "planning")
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"cookbook-drift-{new_sha[:8]}.md"
        report_path.write_text(render_document(new_sha, results), encoding="utf-8")
        print(f"report: {report_path}")
    else:
        print("no drift detected — no report written")

    # Compact stdout summary for the calling skill.
    for r in results:
        if r["status"] == "drift-detected":
            s = r["summary"]
            print(f"  {r['name']}: drift — "
                  f"{s['updated_referenced']} updated, "
                  f"{s['new_specialities_existing']} new-speciality, "
                  f"{s['new_specialist_areas']} new-area, "
                  f"{s['stale_references']} stale")
        else:
            print(f"  {r['name']}: {r['status']}")
    return 1 if errored else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
