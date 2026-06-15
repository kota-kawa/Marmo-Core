#!/usr/bin/env bash
# cleanup.sh — retention policy for attempt JSON files
#
# Keeps:  top N% of attempts by val_bpb (default 50%)
#         all attempts from the last N days (default 7)
# Archives the rest: compresses into shared/attempts/archive/YYYYMMDD.tar.gz
#
# Usage:
#   bash scripts/cleanup.sh                          # defaults
#   bash scripts/cleanup.sh --dry-run               # show what would be archived
#   bash scripts/cleanup.sh --keep-days 14           # keep last 14 days
#   bash scripts/cleanup.sh --keep-top-pct 75        # keep top 75% by metric
#   bash scripts/cleanup.sh --dry-run --keep-days 3  # preview aggressive cleanup
set -euo pipefail

BASE_DIR="${LITMUS_BASE:-$HOME/.litmus}"
SHARED_DIR="$BASE_DIR/shared"
ATTEMPTS_DIR="$SHARED_DIR/attempts"
ARCHIVE_DIR="$ATTEMPTS_DIR/archive"

KEEP_DAYS=7
KEEP_TOP_PCT=50
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)        DRY_RUN=true;           shift ;;
    --keep-days)      KEEP_DAYS="$2";         shift 2 ;;
    --keep-top-pct)   KEEP_TOP_PCT="$2";      shift 2 ;;
    *) shift ;;
  esac
done

mkdir -p "$ARCHIVE_DIR"

echo "=== Litmus Cleanup ==="
echo "Attempts dir:  $ATTEMPTS_DIR"
echo "Keep last:     ${KEEP_DAYS} days"
echo "Keep top:      ${KEEP_TOP_PCT}% by val_bpb"
echo "Dry run:       $DRY_RUN"
echo ""

# Compute which files to archive
TO_ARCHIVE=$(python3 - << EOF
import json, glob, os
from datetime import datetime, timezone, timedelta

attempts_dir = "$ATTEMPTS_DIR"
keep_days = int($KEEP_DAYS)
keep_top_pct = float($KEEP_TOP_PCT) / 100.0
cutoff = datetime.now(timezone.utc) - timedelta(days=keep_days)

records = []
for f in glob.glob(f"{attempts_dir}/*.json"):
    try:
        d = json.load(open(f))
        ts = datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00"))
        bpb = float(d.get("val_bpb", 999))
        records.append({"file": f, "ts": ts, "bpb": bpb})
    except:
        pass  # skip unreadable files

if not records:
    print("NO_RECORDS")
    exit(0)

total = len(records)
print(f"# Total attempt files: {total}", flush=True)

# Always keep: recent files
recent = {r["file"] for r in records if r["ts"] >= cutoff}

# Always keep: top N% by val_bpb (lower is better)
sorted_by_bpb = sorted(records, key=lambda x: x["bpb"])
keep_top_n = max(1, int(total * keep_top_pct))
top_files = {r["file"] for r in sorted_by_bpb[:keep_top_n]}

keep = recent | top_files
archive = [r["file"] for r in records if r["file"] not in keep]

print(f"# Keep (recent):      {len(recent)}")
print(f"# Keep (top {int(keep_top_pct*100)}%):  {len(top_files)}")
print(f"# Keep (union):       {len(keep)}")
print(f"# To archive:         {len(archive)}")
for f in sorted(archive):
    print(f)
EOF
)

# Print summary lines (prefixed with #)
echo "$TO_ARCHIVE" | grep '^#' | sed 's/^# //'
echo ""

# Get just the file paths (lines not starting with #)
ARCHIVE_FILES=$(echo "$TO_ARCHIVE" | grep -v '^#' | grep -v '^NO_RECORDS' | grep '\.json$' || true)

if [ -z "$ARCHIVE_FILES" ]; then
  echo "Nothing to archive."
  exit 0
fi

COUNT=$(echo "$ARCHIVE_FILES" | wc -l | tr -d ' ')
ARCHIVE_NAME="$ARCHIVE_DIR/$(date -u +%Y%m%d-%H%M%S)-archived-${COUNT}.tar.gz"

if [ "$DRY_RUN" = "true" ]; then
  echo "DRY RUN — would archive $COUNT files to:"
  echo "  $ARCHIVE_NAME"
  echo ""
  echo "Files that would be archived:"
  echo "$ARCHIVE_FILES" | head -20
  [ "$(echo "$ARCHIVE_FILES" | wc -l)" -gt 20 ] && echo "  ... and $((COUNT - 20)) more"
  exit 0
fi

# Create archive
echo "Archiving $COUNT files..."
echo "$ARCHIVE_FILES" | xargs tar -czf "$ARCHIVE_NAME" --

# Remove originals after successful archive
echo "$ARCHIVE_FILES" | xargs rm --

ARCHIVE_SIZE=$(du -sh "$ARCHIVE_NAME" | cut -f1)
echo "Archived $COUNT files → $ARCHIVE_NAME ($ARCHIVE_SIZE)"
echo ""

# Log the cleanup
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) cleanup: archived $COUNT attempts → $(basename $ARCHIVE_NAME)" \
  >> "$SHARED_DIR/cleanup-log.txt"

# Report remaining disk usage
USED=$(df -h "$BASE_DIR" | awk 'NR==2 {print $5}')
AVAIL=$(df -h "$BASE_DIR" | awk 'NR==2 {print $4}')
echo "Disk usage after cleanup: ${USED} used, ${AVAIL} available"
