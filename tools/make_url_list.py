#!/usr/bin/env python3
"""Build source-URL lists from skills/manifest.jsonl.

Outputs (in the skills dir):
  - sources.txt : one GitHub blob URL per skill (to its SKILL.md)
  - SOURCES.md  : table of id / name / repo / skill URL / local folder

Safe to run anytime, including while collection is in progress.
GitHub resolves `/blob/HEAD/` to the repo's default branch.
"""
import os
import json
import urllib.parse

OUT_DIR = os.environ.get("OUT_DIR", os.path.join(os.path.dirname(__file__), "..", "skills"))
OUT_DIR = os.path.abspath(OUT_DIR)
MANIFEST = os.path.join(OUT_DIR, "manifest.jsonl")


def blob_url(repo, path):
    return f"https://github.com/{repo}/blob/HEAD/" + urllib.parse.quote(path)


def repo_url(repo):
    return f"https://github.com/{repo}"


def main():
    rows = []
    with open(MANIFEST, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))

    txt = os.path.join(OUT_DIR, "sources.txt")
    with open(txt, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(blob_url(r["repo"], r["path"]) + "\n")

    md = os.path.join(OUT_DIR, "SOURCES.md")
    with open(md, "w", encoding="utf-8") as f:
        f.write(f"# Skill sources ({len(rows)} skills)\n\n")
        f.write("| # | name | repo | skill URL | local |\n")
        f.write("|---|------|------|-----------|-------|\n")
        for r in rows:
            name = (r.get("name") or "").replace("|", "\\|")[:60]
            f.write(f"| {r['id']} | {name} | "
                    f"[{r['repo']}]({repo_url(r['repo'])}) | "
                    f"[SKILL.md]({blob_url(r['repo'], r['path'])}) | "
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
