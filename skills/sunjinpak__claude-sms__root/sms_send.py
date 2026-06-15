#!/usr/bin/env python3
"""Send SMS in bulk from macOS via iPhone+Mac SMS forwarding.

Routes through Continuity (uses your mobile plan, typically $0 cost).
For Android recipients, sends as plain SMS. For iMessage-active numbers,
Messages.app may force-route via iMessage despite --service SMS flag.

Usage:
  python3 sms_send.py <recipients.csv> [--service SMS|iMessage] [--dry-run]
                      [--log-dir DIR] [--throttle SECONDS]
                      [--template-file FILE]

CSV format (header required):
  pid,phone,message
  P001,+15551234567,Custom message text for this recipient

If 'message' column missing, --template-file can supply a default template
with {pid} interpolation.

Logs each send to <log-dir>/sms_log.csv (default: ~/sms_logs/).
"""

import argparse
import csv
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


def normalize_phone(raw):
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 10:
        return "+1" + digits
    if len(digits) == 11 and digits.startswith("1"):
        return "+" + digits
    if raw.startswith("+"):
        return raw
    raise ValueError(f"Invalid phone format: {raw}")


def send_message(phone, message, service):
    safe_msg = message.replace('"', '\\"').replace("\n", " ")
    script = f'''
    tell application "Messages"
        set targetService to 1st service whose service type = {service}
        set targetBuddy to participant "{phone}" of targetService
        send "{safe_msg}" to targetBuddy
    end tell
    '''
    result = subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True, timeout=15
    )
    return result.returncode == 0, (result.stderr or "").strip()


def append_log(log_path, row):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not log_path.exists()
    with open(log_path, "a") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["timestamp", "pid", "phone", "service", "status", "error", "message"])
        w.writerow(row)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv_file", help="CSV with header: pid,phone[,message]")
    p.add_argument("--service", choices=["SMS", "iMessage"], default="SMS",
                   help="Messages service type. Use SMS for Android recipients.")
    p.add_argument("--dry-run", action="store_true",
                   help="Print what would be sent without actually sending.")
    p.add_argument("--log-dir", default=str(Path.home() / "sms_logs"),
                   help="Directory for sms_log.csv (default: ~/sms_logs/)")
    p.add_argument("--throttle", type=int, default=4,
                   help="Seconds to wait between sends (default: 4, helps avoid carrier spam flags)")
    p.add_argument("--template-file",
                   help="Path to a text file with default message template (uses {pid} placeholder).")
    args = p.parse_args()

    log_path = Path(args.log_dir) / "sms_log.csv"

    default_template = None
    if args.template_file:
        with open(args.template_file) as f:
            default_template = f.read().strip()

    with open(args.csv_file) as f:
        rows = list(csv.DictReader(f))

    print(f"Loaded {len(rows)} rows. Service={args.service}. Dry-run={args.dry_run}.")
    if not args.dry_run:
        confirm = input("Send? (y/N): ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return

    for i, row in enumerate(rows, 1):
        pid = row.get("pid", f"row{i}")
        phone = normalize_phone(row["phone"])
        msg = row.get("message") or (default_template.format(pid=pid) if default_template else None)
        if not msg:
            print(f"[{i}] Skip {pid}: no message and no --template-file")
            continue
        ts = datetime.now().isoformat(timespec="seconds")

        if args.dry_run:
            print(f"[DRY {i}/{len(rows)}] {pid} {phone}: {msg[:80]}")
            append_log(log_path, [ts, pid, phone, args.service, "dry-run", "", msg])
            continue

        ok, err = send_message(phone, msg, args.service)
        status = "sent" if ok else "failed"
        print(f"[{i}/{len(rows)}] {pid} {phone} -> {status}" + (f" ({err})" if err else ""))
        append_log(log_path, [ts, pid, phone, args.service, status, err, msg])

        if i < len(rows):
            time.sleep(args.throttle)

    print(f"Done. Log: {log_path}")


if __name__ == "__main__":
    main()
