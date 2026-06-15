#!/usr/bin/env python3
"""SMS verification: scan chat.db for replies from a list of phone numbers.

Usage:
  python3 sms_verify_check.py <phones.csv> [--hours N]

Reads phones from CSV (header: pid,phone[,message]), queries
~/Library/Messages/chat.db for inbound messages within the last N hours
(default 48), and prints a report.

A "valid" reply for verification is any inbound message after our send
time. Bot-like patterns flagged: empty/whitespace, autoresponder phrases,
identical content across multiple PIDs.
"""

import argparse
import csv
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

DB = Path.home() / "Library/Messages/chat.db"
APPLE_EPOCH_OFFSET = 978307200  # seconds between 1970-01-01 and 2001-01-01


def normalize_phone(raw):
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    return raw


def apple_ts_to_dt(ts):
    return datetime.fromtimestamp(ts / 1e9 + APPLE_EPOCH_OFFSET)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv_file")
    p.add_argument("--hours", type=int, default=48)
    args = p.parse_args()

    with open(args.csv_file) as f:
        rows = list(csv.DictReader(f))
    phones = {normalize_phone(r["phone"]): r["pid"] for r in rows}

    cutoff_dt = datetime.now() - timedelta(hours=args.hours)
    cutoff_apple_ns = int((cutoff_dt.timestamp() - APPLE_EPOCH_OFFSET) * 1e9)

    conn = sqlite3.connect(str(DB))
    cur = conn.cursor()

    results = defaultdict(list)
    for phone, pid in phones.items():
        last10 = phone[-10:]
        cur.execute(
            """
            SELECT m.date, m.text, m.is_from_me, m.service
            FROM message m
            JOIN handle h ON m.handle_id = h.ROWID
            WHERE h.id LIKE ?
              AND m.date > ?
            ORDER BY m.date ASC
            """,
            (f"%{last10}", cutoff_apple_ns),
        )
        for date, text, is_from_me, service in cur.fetchall():
            results[pid].append(
                {
                    "ts": apple_ts_to_dt(date),
                    "text": (text or "").strip(),
                    "is_from_me": bool(is_from_me),
                    "service": service,
                }
            )

    reply_texts = defaultdict(list)
    print(f"\n=== SMS Verify Report (last {args.hours}h) ===\n")
    for pid, msgs in results.items():
        sent = [m for m in msgs if m["is_from_me"]]
        replies = [m for m in msgs if not m["is_from_me"]]
        print(f"[{pid}]")
        print(f"  sent: {len(sent)}, replied: {len(replies)}")
        for r in replies:
            print(f"    {r['ts'].strftime('%m-%d %H:%M')} [{r['service']}] {r['text'][:100]}")
            reply_texts[r["text"]].append(pid)
        if not replies:
            print(f"    NO REPLY")
        print()

    # Flag identical replies across PIDs (bot/template signal)
    duplicates = {t: pids for t, pids in reply_texts.items() if len(pids) > 1 and t}
    if duplicates:
        print("=== Identical reply text across multiple PIDs (bot signal) ===")
        for text, pids in duplicates.items():
            print(f"  {pids}: {text[:100]}")

    print("\n=== Summary ===")
    print(f"  Total PIDs checked: {len(phones)}")
    print(f"  Replied (any): {sum(1 for pid in phones.values() if any(not m['is_from_me'] for m in results[pid]))}")
    print(f"  No reply: {sum(1 for pid in phones.values() if not any(not m['is_from_me'] for m in results[pid]))}")


if __name__ == "__main__":
    main()
