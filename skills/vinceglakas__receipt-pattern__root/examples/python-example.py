#!/usr/bin/env python3
"""Minimal Receipt Pattern implementation in Python."""

import json
import os
import secrets
import time
from datetime import datetime, timezone
from typing import Any


def make_receipt_id() -> str:
    return f"rcpt_{int(time.time())}_{secrets.token_hex(3)}"


def write_receipt(receipt: dict[str, Any]) -> str:
    os.makedirs("receipts", exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H-%M-%S")
    actions = receipt.get("actions", [])
    main_type = actions[0]["type"].replace(":", "-") if actions else "unknown"
    path = f"receipts/{ts}-{main_type}.json"
    with open(path, "w") as f:
        json.dump(receipt, f, indent=2)
        f.write("\n")
    return path


def get_last_receipt() -> dict[str, Any] | None:
    if not os.path.isdir("receipts"):
        return None
    files = sorted(f for f in os.listdir("receipts") if f.endswith(".json"))
    if not files:
        return None
    with open(f"receipts/{files[-1]}") as f:
        return json.load(f)


# --- Usage Example ---

if __name__ == "__main__":
    start = time.time()

    # ... your agent does work here ...

    receipt = {
        "id": make_receipt_id(),
        "agentId": "my-python-agent",
        "sessionId": f"sess_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trigger": "manual",
        "status": "completed",
        "durationMs": int((time.time() - start) * 1000),
        "actions": [
            {
                "sequence": 1,
                "type": "db:write",
                "target": "users table",
                "summary": "Migrated 1,204 user records — added email_verified column",
                "status": "success",
                "isRollbackEligible": True,
                "durationMs": 3400,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ],
        "anomalies": [],
        "rollbackAvailable": True,
        "sdkVersion": "receipt-pattern/1.0.0",
    }

    path = write_receipt(receipt)
    print(f"Receipt written: {path}")
