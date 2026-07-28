"""Structured audit log primitives for Marmo-Core."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
import hashlib
import json
import threading
import uuid


REDACTED = "[REDACTED]"

_SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
)

_NON_SECRET_TOKEN_KEYS = {
    "approval_token",
    "estimated_tokens",
    "input_tokens",
    "max_tokens",
    "output_tokens",
    "token_budget",
    "token_count",
    "token_usage",
}


@dataclass(frozen=True)
class AuditRecord:
    """One tamper-evident, JSON-serializable audit event."""

    trace_id: str
    span_id: str
    timestamp: str
    kind: str
    payload: dict[str, Any]
    prev_hash: str | None
    hash: str

    @classmethod
    def create(
        cls,
        *,
        kind: str,
        payload: Mapping[str, Any],
        trace_id: str | None = None,
        span_id: str | None = None,
        prev_hash: str | None = None,
        timestamp: str | None = None,
    ) -> "AuditRecord":
        data = {
            "trace_id": trace_id or uuid.uuid4().hex,
            "span_id": span_id or uuid.uuid4().hex[:16],
            "timestamp": timestamp or _utc_now(),
            "kind": kind,
            "payload": mask_sensitive(payload),
            "prev_hash": prev_hash,
        }
        return cls(hash=_hash_record(data), **data)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AuditRecord":
        payload = data.get("payload")
        if not isinstance(payload, Mapping):
            raise ValueError("audit record payload must be an object")
        prev_hash = data.get("prev_hash")
        if prev_hash is not None and not isinstance(prev_hash, str):
            raise ValueError("audit record prev_hash must be a string or null")
        return cls(
            trace_id=_required_str(data, "trace_id"),
            span_id=_required_str(data, "span_id"),
            timestamp=_required_str(data, "timestamp"),
            kind=_required_str(data, "kind"),
            payload=dict(payload),
            prev_hash=prev_hash,
            hash=_required_str(data, "hash"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "timestamp": self.timestamp,
            "kind": self.kind,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "hash": self.hash,
        }

    def validate_hash(self) -> bool:
        data = self.to_dict()
        expected = data.pop("hash")
        return _hash_record(data) == expected


class AuditLog:
    """Append-only audit log with an in-memory hash chain."""

    def __init__(self, records: Iterable[AuditRecord] = ()) -> None:
        self.records: list[AuditRecord] = list(records)
        # Each record hashes its predecessor, so concurrent appends (parallel
        # plan steps, F-PLAN-05) would interleave into a broken chain.
        self._lock = threading.Lock()

    def append(
        self,
        kind: str,
        payload: Mapping[str, Any],
        *,
        trace_id: str | None = None,
        span_id: str | None = None,
    ) -> AuditRecord:
        with self._lock:
            prev_hash = self.records[-1].hash if self.records else None
            record = AuditRecord.create(
                kind=kind,
                payload=payload,
                trace_id=trace_id,
                span_id=span_id,
                prev_hash=prev_hash,
            )
            self.records.append(record)
            return record

    def verify(self) -> list[str]:
        issues: list[str] = []
        previous_hash: str | None = None
        for index, record in enumerate(self.records):
            if record.prev_hash != previous_hash:
                issues.append(f"record {index} has invalid prev_hash")
            if not record.validate_hash():
                issues.append(f"record {index} has invalid hash")
            previous_hash = record.hash
        return issues

    def write_jsonl(self, path: str | Path) -> None:
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as file:
            for record in self.records:
                json.dump(record.to_dict(), file, ensure_ascii=False, sort_keys=True)
                file.write("\n")

    @classmethod
    def from_jsonl(cls, path: str | Path) -> "AuditLog":
        source = Path(path)
        if not source.exists():
            return cls()
        records: list[AuditRecord] = []
        with source.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"invalid audit JSONL at line {line_number}: {exc}") from exc
                records.append(AuditRecord.from_dict(data))
        audit_log = cls(records)
        issues = audit_log.verify()
        if issues:
            joined = "; ".join(issues)
            raise ValueError(f"invalid audit hash chain: {joined}")
        return audit_log

    @classmethod
    def append_jsonl(
        cls,
        path: str | Path,
        kind: str,
        payload: Mapping[str, Any],
        *,
        trace_id: str | None = None,
        span_id: str | None = None,
    ) -> AuditRecord:
        destination = Path(path)
        audit_log = cls.from_jsonl(destination)
        record = audit_log.append(kind, payload, trace_id=trace_id, span_id=span_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("a", encoding="utf-8") as file:
            json.dump(record.to_dict(), file, ensure_ascii=False, sort_keys=True)
            file.write("\n")
        return record


def mask_sensitive(value: Any) -> Any:
    """Return a JSON-friendly copy with secret-like fields redacted."""

    if isinstance(value, Mapping):
        masked: dict[str, Any] = {}
        for key, item in value.items():
            key_string = str(key)
            if _is_sensitive_key(key_string):
                masked[key_string] = REDACTED
            else:
                masked[key_string] = mask_sensitive(item)
        return masked
    if isinstance(value, (list, tuple)):
        return [mask_sensitive(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _is_sensitive_key(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    if normalized in _NON_SECRET_TOKEN_KEYS:
        return False
    return any(part in normalized for part in _SENSITIVE_KEY_PARTS)


def _hash_record(data: Mapping[str, Any]) -> str:
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _required_str(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"audit record {key} must be a non-empty string")
    return value
