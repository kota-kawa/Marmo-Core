#!/usr/bin/env python3
"""Collect Agent Skills (SKILL.md + sibling files) from across GitHub.

Strategy (rate-limit aware, stdlib only):
  1. Discover repos via GitHub *code search* for SKILL.md (varied queries to
     get past the 1000-result-per-query cap and maximize diversity).
  2. For each unique repo, resolve the default branch to one commit SHA and
     fetch that commit's recursive git tree once. Everything else for the repo
     (file downloads, the manifest, the source URLs) uses that SHA, never the
     branch name, so a push in the middle of a run cannot mix two revisions.
     Use `--commit owner/repo=SHA` to collect a specific commit instead.
  3. For every directory that contains a SKILL.md, download the whole skill
     folder via raw.githubusercontent.com (raw fetches are NOT rate limited).
     Every file must arrive, match its git blob SHA from the tree, and match
     again when read back from disk; only then is the folder moved into place
     and recorded in the manifest. A skill that fails any step is left out.
  4. Dedup skills by SKILL.md content hash; stop once TARGET is reached.

Output goes to <repo>/resources/skills (the benchmark default; git-ignored and
not shipped). Override with OUT_DIR.

Auth: expects a GitHub token in env GH_TOKEN (e.g. `GH_TOKEN=$(gh auth token)`).
"""
import argparse
import os
import re
import shutil
import sys
import json
import time
import hashlib
import threading
import urllib.request
import urllib.parse
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

TARGET = int(os.environ.get("TARGET", "1000"))
OUT_DIR = os.environ.get("OUT_DIR", os.path.join(os.path.dirname(__file__), "..", "resources", "skills"))
OUT_DIR = os.path.abspath(OUT_DIR)
MANIFEST = os.path.join(OUT_DIR, "manifest.jsonl")
STATE = os.path.join(OUT_DIR, ".state.json")
def _read_token():
    t = os.environ.get("GH_TOKEN", "").strip()
    # Old gh lacks `gh auth token`; fall back to hosts.yml.
    if not t or " " in t:
        for p in (os.path.expanduser("~/.config/gh/hosts.yml"),):
            try:
                m = re.search(r"oauth_token:\s*(\S+)", open(p).read())
                if m:
                    return m.group(1).strip()
            except OSError:
                pass
    return t


TOKEN = _read_token()
MAX_FILE = 25 * 1024 * 1024  # skip only very large blobs (keep all scripts/assets)
SKILL_NAME = "skill.md"     # matched case-insensitively

API = "https://api.github.com"
RAW = "https://raw.githubusercontent.com"

# Only redistribute skills under permissive licenses ("completely fine").
ALLOW_LICENSES = {
    "MIT", "MIT-0", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
    "BSD-3-Clause-Clear", "ISC", "0BSD", "Unlicense", "CC0-1.0", "Zlib",
}

REPO_WORKERS = int(os.environ.get("REPO_WORKERS", "16"))
FILE_WORKERS = int(os.environ.get("FILE_WORKERS", "8"))
STOP = threading.Event()

# Varied code-search queries. Each is capped at 1000 results by GitHub, so we
# partition by size and sort order to surface different repos -> more diversity.
QUERIES = [
    "filename:SKILL.md",
    "filename:SKILL.md size:<800",
    "filename:SKILL.md size:800..2000",
    "filename:SKILL.md size:2000..5000",
    "filename:SKILL.md size:>5000",
    "filename:SKILL.md path:skills",
    "filename:SKILL.md path:.claude",
    "filename:SKILL.md description name",
]


def log(*a):
    print(*a, flush=True)


def req(url, accept="application/vnd.github+json"):
    r = urllib.request.Request(url)
    r.add_header("Accept", accept)
    r.add_header("User-Agent", "marmo-skill-collector")
    if TOKEN:
        r.add_header("Authorization", f"Bearer {TOKEN}")
    return r


def api_get(path, params=None, raw=False, retries=4):
    url = path if path.startswith("http") else API + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req(url), timeout=60) as resp:
                hdr = resp.headers
                data = resp.read()
                # Respect search secondary limits proactively.
                remain = hdr.get("X-RateLimit-Remaining")
                reset = hdr.get("X-RateLimit-Reset")
                if remain is not None and int(remain) <= 1 and reset:
                    wait = max(0, int(reset) - int(time.time())) + 2
                    log(f"  [rate] sleeping {wait}s")
                    time.sleep(wait)
                return data if raw else json.loads(data)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429):
                reset = e.headers.get("X-RateLimit-Reset")
                wait = 30
                if reset:
                    wait = max(5, int(reset) - int(time.time()) + 2)
                log(f"  [rate {e.code}] sleeping {min(wait,90)}s")
                time.sleep(min(wait, 90))
                continue
            if e.code in (404, 451, 409):
                return None
            log(f"  [http {e.code}] {url}")
            time.sleep(3)
        except Exception as ex:
            log(f"  [err] {ex}")
            time.sleep(3)
    return None


COMMIT_RE = re.compile(r"[0-9a-f]{40}")


def raw_get(repo, commit, path):
    url = f"{RAW}/{repo}/{commit}/{urllib.parse.quote(path)}"
    try:
        with urllib.request.urlopen(req(url, accept="*/*"), timeout=60) as resp:
            return resp.read()
    except Exception:
        return None


def discover_repos():
    repos = []
    seen = set()
    for q in QUERIES:
        for order in ("desc", "asc"):
            for page in range(1, 11):  # up to 1000 results per (q,order)
                d = api_get("/search/code", {
                    "q": q, "per_page": 100, "page": page,
                    "sort": "indexed", "order": order,
                })
                time.sleep(6.5)  # code search ~10/min
                if not d or "items" not in d:
                    break
                items = d["items"]
                if not items:
                    break
                for it in items:
                    full = it["repository"]["full_name"]
                    if full not in seen:
                        seen.add(full)
                        repos.append(full)
                log(f"  [discover] q='{q}' order={order} p{page}: "
                    f"+{len(items)} items, {len(repos)} unique repos")
                if len(items) < 100:
                    break
        log(f"[discover] after '{q}': {len(repos)} repos")
    return repos


def load_state():
    done_repos, skill_hashes, count = set(), set(), 0
    if os.path.exists(STATE):
        with open(STATE) as f:
            s = json.load(f)
        done_repos = set(s.get("done_repos", []))
        skill_hashes = set(s.get("skill_hashes", []))
        count = s.get("count", 0)
    return done_repos, skill_hashes, count


def save_state(done_repos, skill_hashes, count):
    with open(STATE, "w") as f:
        json.dump({
            "done_repos": sorted(done_repos),
            "skill_hashes": sorted(skill_hashes),
            "count": count,
        }, f)


def _scalar(lines, i):
    """Return (value, next_index). Handles inline and |/> block scalars."""
    key, _, rest = lines[i].partition(":")
    rest = rest.strip()
    if rest and rest[0] in "|>":
        # block scalar: collect indented following lines
        body, j = [], i + 1
        while j < len(lines) and (lines[j].strip() == "" or
                                  lines[j][:1] in (" ", "\t")):
            body.append(lines[j].strip())
            j += 1
        return " ".join(x for x in body if x), j
    return rest.strip('"\''), i + 1


def parse_frontmatter(text):
    name = desc = ""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            lines = text[3:end].splitlines()
            i = 0
            while i < len(lines):
                low = lines[i].strip().lower()
                if low.startswith("name:") and not name:
                    name, i = _scalar(lines, i)
                    continue
                if low.startswith("description:") and not desc:
                    desc, i = _scalar(lines, i)
                    continue
                i += 1
    return name, desc


def sanitize(s):
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in s)[:120]


def git_blob_sha(data):
    """The git object id of a blob, as listed in a git tree."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


class Ctx:
    def __init__(self, skill_hashes, done_repos, count, mf, out_dir=None, pins=None):
        self.skill_hashes = skill_hashes
        self.inflight = set()
        self.done_repos = done_repos
        self.count = count
        self.mf = mf
        self.out_dir = out_dir or OUT_DIR
        self.pins = pins or {}
        self.lock = threading.Lock()


def _fetch_verified(repo, commit, path, blob_sha):
    """Return the blob's bytes, or None unless they hash to the tree's blob SHA."""
    data = raw_get(repo, commit, path)
    if data is None:
        log(f"  [skip] {repo}@{commit[:8]}:{path}: download failed")
        return None
    if git_blob_sha(data) != blob_sha:
        log(f"  [skip] {repo}@{commit[:8]}:{path}: content does not match tree blob {blob_sha[:8]}")
        return None
    return data


def _download_files(repo, commit, sdir, blobs, known=None):
    """Fetch all blobs under a skill dir in parallel.

    Returns ({rel_path: bytes}, [rel_path of blobs over MAX_FILE]), or None if
    any blob that should have been fetched is missing or does not match its
    git blob SHA. `known` maps repo paths to bytes that were already fetched
    and verified.
    """
    known = known or {}
    out, skipped, todo = {}, [], []
    for p, size, blob_sha in blobs:
        rel = p[len(sdir):].lstrip("/") if sdir else p
        if p in known:
            out[rel] = known[p]
        elif size and size > MAX_FILE:
            skipped.append(rel)
        else:
            todo.append((p, rel, blob_sha))

    workers = min(FILE_WORKERS, max(1, len(todo)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        fetched = list(ex.map(lambda t: _fetch_verified(repo, commit, t[0], t[2]), todo))
    for (_, rel, _), data in zip(todo, fetched):
        if data is None:
            return None
        out[rel] = data
    return out, sorted(skipped)


def _write_file(path, content):
    with open(path, "wb") as f:
        f.write(content)


def _store(tmp, files, blob_shas):
    """Write files under tmp and read each one back; True only if all bytes match."""
    for rel, content in files.items():
        fp = os.path.join(tmp, rel)
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        _write_file(fp, content)
    for rel, blob_sha in blob_shas.items():
        with open(os.path.join(tmp, rel), "rb") as f:
            if git_blob_sha(f.read()) != blob_sha:
                return False
    return True


def resolve_commit(repo, branch, ctx):
    """The commit every later request for this repo uses: the pinned SHA, else the branch head now."""
    pinned = ctx.pins.get(repo)
    if pinned:
        return pinned
    head = api_get(f"/repos/{repo}/commits/{urllib.parse.quote(branch, safe='')}")
    sha = (head or {}).get("sha", "")
    return sha if COMMIT_RE.fullmatch(sha) else None


def process_repo(repo, ctx):
    """Collect the skills of one repo. True when the repo was fully handled (nothing failed or was cut short)."""
    if STOP.is_set():
        return False
    info = api_get(f"/repos/{repo}")
    if not info:
        return False
    lic = (info.get("license") or {}).get("spdx_id")
    if lic not in ALLOW_LICENSES:
        return True  # skip non-permissive / unlicensed repos
    branch = info.get("default_branch", "main")
    commit = resolve_commit(repo, branch, ctx)
    if not commit:
        log(f"  [skip] {repo}: could not resolve a commit for {branch}")
        return False
    tree = api_get(f"/repos/{repo}/git/trees/{commit}", {"recursive": "1"})
    if not tree or "tree" not in tree:
        return False
    if tree.get("truncated"):
        log(f"  [skip] {repo}@{commit[:8]}: git tree is truncated, the file list would be incomplete")
        return False
    entries = tree["tree"]
    skill_dirs = {}
    for e in entries:
        if e["type"] == "blob" and os.path.basename(e["path"]).lower() == SKILL_NAME:
            skill_dirs[os.path.dirname(e["path"])] = []
    if not skill_dirs:
        return True
    for e in entries:
        if e["type"] != "blob":
            continue
        cur = os.path.dirname(e["path"])
        while True:
            if cur in skill_dirs:
                skill_dirs[cur].append((e["path"], e.get("size", 0), e["sha"]))
                break
            if not cur:
                break
            cur = os.path.dirname(cur)

    complete = True
    for sdir, blobs in skill_dirs.items():
        if STOP.is_set():
            return False
        if not _collect_skill(repo, branch, commit, lic, sdir, blobs, ctx):
            complete = False
    return complete


def _collect_skill(repo, branch, commit, lic, sdir, blobs, ctx):
    """Collect one skill folder. False when it could not be completed."""
    skill_md, skill_size, skill_sha = next(b for b in blobs if os.path.basename(b[0]).lower() == SKILL_NAME)
    if skill_size and skill_size > MAX_FILE:
        log(f"  [skip] {repo}@{commit[:8]}:{skill_md}: SKILL.md is over {MAX_FILE} bytes")
        return False
    md = _fetch_verified(repo, commit, skill_md, skill_sha)
    if md is None:
        return False
    h = hashlib.sha256(md).hexdigest()
    with ctx.lock:
        if h in ctx.skill_hashes or h in ctx.inflight:
            return True
        ctx.inflight.add(h)
    tmp = None
    try:
        name, desc = parse_frontmatter(md.decode("utf-8", "replace"))
        downloaded = _download_files(repo, commit, sdir, blobs, known={skill_md: md})
        if downloaded is None:
            return False
        files, skipped = downloaded
        blob_shas = {
            (p[len(sdir):].lstrip("/") if sdir else p): blob_sha for p, _, blob_sha in blobs
        }
        os.makedirs(ctx.out_dir, exist_ok=True)
        tmp = os.path.join(ctx.out_dir, f".partial-{os.getpid()}-{threading.get_ident()}")
        shutil.rmtree(tmp, ignore_errors=True)
        if not _store(tmp, files, {rel: blob_shas[rel] for rel in files}):
            log(f"  [skip] {repo}@{commit[:8]}:{sdir or '/'}: stored bytes differ from what was downloaded")
            return False
        owner, rname = repo.split("/", 1)
        base = sanitize(f"{owner}__{rname}__{os.path.basename(sdir) or 'root'}")
        with ctx.lock:
            if STOP.is_set():
                return False
            folder = base
            if os.path.exists(os.path.join(ctx.out_dir, folder)):
                folder = f"{base}__{h[:8]}"
            dest = os.path.join(ctx.out_dir, folder)
            os.replace(tmp, dest)
            tmp = None
            ctx.count += 1
            cid = ctx.count
            if ctx.count >= TARGET:
                STOP.set()
            ctx.skill_hashes.add(h)
            ctx.mf.write(json.dumps({
                "id": cid,
                "name": name,
                "description": desc,
                "repo": repo,
                "branch": branch,
                "commit": commit,
                "license": lic,
                "path": skill_md,
                "local": folder,
                "files": len(files),
                "skipped_oversize": skipped,
                "sha256": h,
            }, ensure_ascii=False) + "\n")
            ctx.mf.flush()
        log(f"[{cid}/{TARGET}] {repo}@{commit[:8]}:{sdir or '/'}  ({len(files)} files)  {name[:50]}")
        return True
    finally:
        with ctx.lock:
            ctx.inflight.discard(h)
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def parse_pins(values):
    """Turn ['owner/repo=<40-hex sha>', ...] into {repo: sha}; ValueError on a malformed entry."""
    pins = {}
    for value in values:
        repo, sep, sha = value.partition("=")
        if not sep or repo.count("/") != 1 or not COMMIT_RE.fullmatch(sha):
            raise ValueError(f"expected owner/repo=<40-hex commit sha>, got {value!r}")
        pins[repo] = sha
    return pins


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--commit", action="append", default=[], metavar="OWNER/REPO=SHA",
                        help="collect this exact commit of a repo instead of its default branch head")
    try:
        pins = parse_pins(parser.parse_args(argv).commit)
    except ValueError as err:
        parser.error(str(err))
    if not TOKEN:
        log("ERROR: set GH_TOKEN (e.g. GH_TOKEN=$(gh auth token))")
        sys.exit(1)
    os.makedirs(OUT_DIR, exist_ok=True)
    done_repos, skill_hashes, count = load_state()
    log(f"=== start: have {count} skills, {len(done_repos)} repos done ===")

    repo_cache = os.path.join(OUT_DIR, ".repos.json")
    if os.path.exists(repo_cache):
        with open(repo_cache) as f:
            repos = json.load(f)
        log(f"loaded {len(repos)} cached repos")
    else:
        log("discovering repos via code search ...")
        repos = discover_repos()
        with open(repo_cache, "w") as f:
            json.dump(repos, f)
        log(f"discovered {len(repos)} repos")

    repos += [r for r in pins if r not in repos]
    if count >= TARGET:
        STOP.set()
    mf = open(MANIFEST, "a", encoding="utf-8")
    ctx = Ctx(skill_hashes, done_repos, count, mf, OUT_DIR, pins)
    pending = [r for r in repos if r not in done_repos]
    log(f"processing {len(pending)} repos with {REPO_WORKERS} workers ...")
    try:
        with ThreadPoolExecutor(max_workers=REPO_WORKERS) as ex:
            fut_map = {ex.submit(process_repo, r, ctx): r for r in pending}
            processed = 0
            for fut in as_completed(fut_map):
                repo = fut_map[fut]
                try:
                    finished = fut.result()
                except Exception as ex_err:
                    log(f"  [repo err] {repo}: {ex_err}")
                    finished = False
                if finished:  # a repo that failed or was cut short is retried on the next run
                    with ctx.lock:
                        ctx.done_repos.add(repo)
                processed += 1
                if processed % 25 == 0:
                    save_state(ctx.done_repos, ctx.skill_hashes, ctx.count)
                if STOP.is_set():
                    break
    finally:
        save_state(ctx.done_repos, ctx.skill_hashes, ctx.count)
        mf.close()
    count = ctx.count
    log(f"=== done: {count} skills collected into {OUT_DIR} ===")
    if count < TARGET:
        log("NOTE: ran out of discovered repos before reaching target. "
            "Re-run after deleting .repos.json to discover more, or add queries.")


if __name__ == "__main__":
    main()
