#!/usr/bin/env python3
"""Collect Agent Skills (SKILL.md + sibling files) from across GitHub.

Strategy (rate-limit aware, stdlib only):
  1. Discover repos via GitHub *code search* for SKILL.md (varied queries to
     get past the 1000-result-per-query cap and maximize diversity).
  2. For each unique repo, fetch the recursive git tree once (1 core call).
  3. For every directory that contains a SKILL.md, download the whole skill
     folder via raw.githubusercontent.com (raw fetches are NOT rate limited).
  4. Dedup skills by SKILL.md content hash; stop once TARGET is reached.

Auth: expects a GitHub token in env GH_TOKEN (e.g. `GH_TOKEN=$(gh auth token)`).
"""
import os
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
OUT_DIR = os.environ.get("OUT_DIR", os.path.join(os.path.dirname(__file__), "..", "skills"))
OUT_DIR = os.path.abspath(OUT_DIR)
MANIFEST = os.path.join(OUT_DIR, "manifest.jsonl")
STATE = os.path.join(OUT_DIR, ".state.json")
def _read_token():
    t = os.environ.get("GH_TOKEN", "").strip()
    # Old gh lacks `gh auth token`; fall back to hosts.yml.
    if not t or " " in t:
        import re
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


def raw_get(repo, branch, path):
    url = f"{RAW}/{repo}/{branch}/{urllib.parse.quote(path)}"
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


class Ctx:
    def __init__(self, skill_hashes, done_repos, count, mf):
        self.skill_hashes = skill_hashes
        self.done_repos = done_repos
        self.count = count
        self.mf = mf
        self.lock = threading.Lock()


def _download_files(repo, branch, sdir, blobs):
    """Fetch all blobs under a skill dir in parallel. Returns {rel_path: bytes}."""
    out = {}

    def fetch(item):
        p, size = item
        if size and size > MAX_FILE:
            return None
        return p, raw_get(repo, branch, p)

    workers = min(FILE_WORKERS, max(1, len(blobs)))
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for res in ex.map(fetch, blobs):
            if res and res[1] is not None:
                p = res[0]
                rel = p[len(sdir):].lstrip("/") if sdir else p
                out[rel] = res[1]
    return out


def process_repo(repo, ctx):
    if STOP.is_set():
        return
    info = api_get(f"/repos/{repo}")
    if not info:
        return
    branch = info.get("default_branch", "main")
    tree = api_get(f"/repos/{repo}/git/trees/{branch}", {"recursive": "1"})
    if not tree or "tree" not in tree:
        return
    entries = tree["tree"]
    skill_dirs = {}
    for e in entries:
        if e["type"] == "blob" and os.path.basename(e["path"]).lower() == SKILL_NAME:
            skill_dirs[os.path.dirname(e["path"])] = []
    if not skill_dirs:
        return
    for e in entries:
        if e["type"] != "blob":
            continue
        cur = os.path.dirname(e["path"])
        while True:
            if cur in skill_dirs:
                skill_dirs[cur].append((e["path"], e.get("size", 0)))
                break
            if not cur:
                break
            cur = os.path.dirname(cur)

    for sdir, blobs in skill_dirs.items():
        if STOP.is_set():
            return
        skill_md = next((p for p, _ in blobs
                         if os.path.basename(p).lower() == SKILL_NAME), None)
        if not skill_md:
            continue
        md = raw_get(repo, branch, skill_md)
        if not md:
            continue
        h = hashlib.sha256(md).hexdigest()
        with ctx.lock:
            if h in ctx.skill_hashes:
                continue
            ctx.skill_hashes.add(h)
        name, desc = parse_frontmatter(md.decode("utf-8", "replace"))
        files = _download_files(repo, branch, sdir, blobs)
        if not files:
            continue
        owner, rname = repo.split("/", 1)
        with ctx.lock:
            if STOP.is_set():
                return
            ctx.count += 1
            cid = ctx.count
            if ctx.count >= TARGET:
                STOP.set()
        folder = sanitize(f"{owner}__{rname}__{os.path.basename(sdir) or 'root'}")
        dest = os.path.join(OUT_DIR, folder)
        if os.path.exists(dest):
            folder = f"{folder}__{h[:8]}"
            dest = os.path.join(OUT_DIR, folder)
        for rel, content in files.items():
            fp = os.path.join(dest, rel)
            os.makedirs(os.path.dirname(fp) or dest, exist_ok=True)
            with open(fp, "wb") as f:
                f.write(content)
        with ctx.lock:
            ctx.mf.write(json.dumps({
                "id": cid,
                "name": name,
                "description": desc,
                "repo": repo,
                "path": skill_md,
                "local": folder,
                "files": len(files),
                "sha256": h,
            }, ensure_ascii=False) + "\n")
            ctx.mf.flush()
        log(f"[{cid}/{TARGET}] {repo}:{sdir or '/'}  ({len(files)} files)  {name[:50]}")


def main():
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

    if count >= TARGET:
        STOP.set()
    mf = open(MANIFEST, "a", encoding="utf-8")
    ctx = Ctx(skill_hashes, done_repos, count, mf)
    pending = [r for r in repos if r not in done_repos]
    log(f"processing {len(pending)} repos with {REPO_WORKERS} workers ...")
    try:
        with ThreadPoolExecutor(max_workers=REPO_WORKERS) as ex:
            fut_map = {ex.submit(process_repo, r, ctx): r for r in pending}
            processed = 0
            for fut in as_completed(fut_map):
                repo = fut_map[fut]
                try:
                    fut.result()
                except Exception as ex_err:
                    log(f"  [repo err] {repo}: {ex_err}")
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
