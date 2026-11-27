#!/usr/bin/env python3
"""Build source-URL lists from resources/skills/manifest.jsonl.

Outputs (in the skills dir, <repo>/resources/skills unless OUT_DIR is set):
  - sources.txt : one GitHub blob URL per skill (to its SKILL.md)
  - SOURCES.md  : table of id / name / repo / commit / skill URL / local folder

Every URL points at the commit recorded in the manifest, so it keeps showing
the revision that was collected even after the branch moves. A manifest row
without a commit (written by an older collector) cannot be pinned, so the run
fails instead of falling back to the moving default branch.

Safe to run anytime, including while collection is in progress.
"""
import os
import sys
import json
import urllib.parse

OUT_DIR = os.environ.get("OUT_DIR", os.path.join(os.path.dirname(__file__), "..", "resources", "skills"))
OUT_DIR = os.path.abspath(OUT_DIR)
MANIFEST = os.path.join(OUT_DIR, "manifest.jsonl")


def blob_url(repo, commit, path):
    return f"https://github.com/{repo}/blob/{commit}/" + urllib.parse.quote(path)


def repo_url(repo):
    return f"https://github.com/{repo}"


def load_rows(manifest):
    """Read the manifest; ValueError if any row lacks the commit its URL must point at."""
    rows = []
    with open(manifest, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    unpinned = [str(r.get("id")) for r in rows if not r.get("commit")]
    if unpinned:
        raise ValueError(
            f"{len(unpinned)} manifest row(s) have no commit (ids: {', '.join(unpinned[:10])}"
            f"{', ...' if len(unpinned) > 10 else ''}); re-collect them with tools/collect_skills.py"
        )
    return rows


def main():
    try:
        rows = load_rows(MANIFEST)
    except ValueError as err:
        sys.exit(f"error: {err}")

    txt = os.path.join(OUT_DIR, "sources.txt")
    with open(txt, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(blob_url(r["repo"], r["commit"], r["path"]) + "\n")

    md = os.path.join(OUT_DIR, "SOURCES.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write(f"# Skill sources ({len(rows)} skills)\n\n")
        f.write("| # | name | repo | commit | skill URL | local |\n")
        f.write("|---|------|------|--------|-----------|-------|\n")
        for r in rows:
            name = (r.get("name") or "").replace("|", "\\|")[:60]
            f.write(f"| {r['id']} | {name} | "
                    f"[{r['repo']}]({repo_url(r['repo'])}) | "
                    f"`{r['commit'][:12]}` | "
                    f"[SKILL.md]({blob_url(r['repo'], r['commit'], r['path'])}) | "
                    f"`{r['local']}` |\n")

    # also a deduped list of unique source repos
    repos = sorted({r["repo"] for r in rows})
    with open(os.path.join(OUT_DIR, "source_repos.txt"), "w", encoding="utf-8") as f:
        for rp in repos:
            f.write(repo_url(rp) + "\n")

    print(f"wrote {len(rows)} skill URLs -> sources.txt")
    print(f"wrote SOURCES.md ({len(rows)} rows)")
    print(f"wrote {len(repos)} unique repo URLs -> source_repos.txt")


if __name__ == "__main__":
    main()
