"""State Store: durable, event-sourced task state (4.9).

Events are the source of truth (F-STATE-03); ``TaskState`` is a projection
folded from them, so any past point is reproducible via ``replay``. A
checkpoint is just a marked sequence number and a rollback is an append-only
event pointing back at one (F-STATE-04) -- the log is never rewritten, which
keeps it consistent with the audit chain's append-only stance.

Backends implement four small hooks (event read / write, task listing,
session storage); the projection, optimistic locking, checkpoint, and
rollback logic is shared (F-STATE-05). Three ship here: in-memory, JSONL
files, and ``sqlite3`` -- all standard library.

Short-term state (``TaskState.variables``, task-scoped) is kept distinct from
long-term state (``remember`` / ``recall``, session-scoped). Knowledge that
outlives a session belongs in the Resource Registry as a Memory resource
rather than here (F-STATE-06).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping
import json
import sqlite3
import threading
import uuid

from .errors import MarmoError
from .secrets import ensure_secret_refs, serialize_secret_refs


SCHEMA_VERSION = 1

TASK_STATUSES = (
    "submitted",
    "running",
    "completed",
    "denied",
    "escalated",
    "failed",
    "cancelled",
)

TERMINAL_STATUSES = ("completed", "denied", "failed", "cancelled")

EVENT_KINDS = (
    "created",
    "status",
    "variable",
    "activated",
    "step",
    "plan",
    "frame",
    "paused",
    "resumed",
    "checkpoint",
    "rollback",
)


class StateConflictError(MarmoError):
    """Raised when a write loses an optimistic-locking race (F-STATE-07)."""


class TaskNotFoundError(MarmoError):
    """Raised when a task id is absent from the store."""


@dataclass(frozen=True)
class StateEvent:
    """One immutable state transition (F-STATE-03)."""

    task_id: str
    seq: int
    timestamp: str
    kind: str
    payload: dict[str, Any]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "StateEvent":
        payload = data.get("payload")
        if not isinstance(payload, Mapping):
            raise ValueError("state event payload must be an object")
        seq = data.get("seq")
        if not isinstance(seq, int):
            raise ValueError("state event seq must be an integer")
        return cls(
            task_id=_required_str(data, "task_id"),
            seq=seq,
            timestamp=_required_str(data, "timestamp"),
            kind=_required_str(data, "kind"),
            payload=dict(payload),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "task_id": self.task_id,
            "seq": self.seq,
            "timestamp": self.timestamp,
            "kind": self.kind,
            "payload": self.payload,
        }


@dataclass(frozen=True)
class TaskState:
    """Projection of one task's events (F-STATE-01).

    ``version`` is the sequence number of the last applied event and is what
    optimistic writes are checked against (F-STATE-07).
    """

    task_id: str
    goal: str
    status: str = "submitted"
    version: int = 0
    session_id: str = ""
    trace_id: str = ""
    detail: str = ""
    output: str = ""
    variables: dict[str, Any] = field(default_factory=dict)
    activated: tuple[str, ...] = ()
    approvals: tuple[str, ...] = ()
    operation_approvals: tuple[str, ...] = ()
    granted_permissions: tuple[str, ...] = ()
    step_results: tuple[dict[str, Any], ...] = ()
    plan: dict[str, Any] | None = None
    frame: dict[str, Any] = field(default_factory=dict)
    pending: dict[str, Any] | None = None
    created_at: str = ""
    updated_at: str = ""

    @property
    def terminal(self) -> bool:
        return self.status in TERMINAL_STATUSES

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "status": self.status,
            "version": self.version,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "detail": self.detail,
            "output": self.output,
            "variables": dict(self.variables),
            "activated": list(self.activated),
            "approvals": list(self.approvals),
            "operation_approvals": list(self.operation_approvals),
            "granted_permissions": list(self.granted_permissions),
            "step_results": [dict(item) for item in self.step_results],
            "plan": dict(self.plan) if self.plan else None,
            "frame": dict(self.frame),
            "pending": dict(self.pending) if self.pending else None,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class Checkpoint:
    """A named point in the event log that ``rollback`` can return to."""

    task_id: str
    seq: int
    label: str
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        return {"task_id": self.task_id, "seq": self.seq, "label": self.label, "timestamp": self.timestamp}


class StateStore(ABC):
    """Event-sourced task state with pluggable persistence (F-STATE-05).

    Subclasses implement the storage hooks only; projection, locking,
    checkpoints, and rollback are shared.
    """

    def __init__(self) -> None:
        # Appending reads the current sequence and then writes the next one.
        # Parallel plan steps (F-PLAN-05) append concurrently, so the pair has
        # to be atomic or two steps race for the same seq.
        self._mutation_lock = threading.RLock()

    # -- storage hooks ------------------------------------------------------

    @abstractmethod
    def _read_events(self, task_id: str) -> list[StateEvent]:
        """Return every event for ``task_id`` in sequence order."""

    @abstractmethod
    def _write_event(self, event: StateEvent) -> None:
        """Persist one event, raising StateConflictError if seq is taken."""

    @abstractmethod
    def task_ids(self) -> list[str]:
        """Return the ids of every known task."""

    @abstractmethod
    def _read_session(self, session_id: str) -> dict[str, Any]:
        """Return long-term session values (F-STATE-06)."""

    @abstractmethod
    def _write_session(self, session_id: str, data: Mapping[str, Any]) -> None:
        """Persist long-term session values (F-STATE-06)."""

    # -- lifecycle ----------------------------------------------------------

    def create(self, goal: str, *, task_id: str | None = None, session_id: str = "") -> TaskState:
        if not goal or not goal.strip():
            raise ValueError("goal must be a non-empty string")
        ensure_secret_refs({"goal": goal})
        task_id = task_id or uuid.uuid4().hex[:12]
        if self._read_events(task_id):
            raise ValueError(f"task id already exists: {task_id}")
        self._write_event(
            StateEvent(
                task_id=task_id,
                seq=1,
                timestamp=_utc_now(),
                kind="created",
                payload={"goal": goal.strip(), "session_id": session_id},
            )
        )
        return self.load(task_id)

    def load(self, task_id: str) -> TaskState:
        events = self._read_events(task_id)
        if not events:
            raise TaskNotFoundError(
                f"unknown task id: {task_id}; submit a goal first, or check the state store path"
            )
        return _project(events)

    def exists(self, task_id: str) -> bool:
        return bool(self._read_events(task_id))

    def events(self, task_id: str) -> list[StateEvent]:
        return self._read_events(task_id)

    def append(
        self,
        task_id: str,
        kind: str,
        payload: Mapping[str, Any] | None = None,
        *,
        expected_version: int | None = None,
    ) -> TaskState:
        """Append one event, optionally guarded by an optimistic version check."""

        if kind not in EVENT_KINDS:
            raise ValueError(f"kind must be one of: {', '.join(EVENT_KINDS)}")
        safe_payload = serialize_secret_refs(dict(payload or {}))
        ensure_secret_refs(safe_payload)
        with self._mutation_lock:
            events = self._read_events(task_id)
            if not events:
                raise TaskNotFoundError(f"unknown task id: {task_id}")
            current = events[-1].seq
            if expected_version is not None and expected_version != current:
                raise StateConflictError(
                    f"task {task_id} moved from version {expected_version} to {current}; "
                    "reload the state and retry the write"
                )
            self._write_event(
                StateEvent(
                    task_id=task_id,
                    seq=current + 1,
                    timestamp=_utc_now(),
                    kind=kind,
                    payload=safe_payload,
                )
            )
            return self.load(task_id)

    def replay(self, task_id: str, *, until_seq: int | None = None) -> TaskState:
        """Rebuild the state as it stood at ``until_seq`` (F-STATE-03)."""

        events = self._read_events(task_id)
        if not events:
            raise TaskNotFoundError(f"unknown task id: {task_id}")
        if until_seq is not None:
            events = [event for event in events if event.seq <= until_seq]
            if not events:
                raise ValueError(f"no events at or before seq {until_seq} for task {task_id}")
        return _project(events)

    # -- checkpoints --------------------------------------------------------

    def checkpoint(self, task_id: str, label: str = "") -> Checkpoint:
        state = self.append(task_id, "checkpoint", {"label": label})
        return Checkpoint(task_id=task_id, seq=state.version, label=label, timestamp=state.updated_at)

    def checkpoints(self, task_id: str) -> list[Checkpoint]:
        return [
            Checkpoint(
                task_id=task_id,
                seq=event.seq,
                label=str(event.payload.get("label", "")),
                timestamp=event.timestamp,
            )
            for event in self._read_events(task_id)
            if event.kind == "checkpoint"
        ]

    def rollback(self, task_id: str, target: int | str) -> TaskState:
        """Return the task to a checkpoint by appending a rollback event (F-STATE-04)."""

        available = self.checkpoints(task_id)
        if isinstance(target, str):
            matches = [item for item in available if item.label == target]
            if not matches:
                labels = ", ".join(sorted({item.label for item in available if item.label})) or "none"
                raise ValueError(f"no checkpoint labeled {target!r} for task {task_id}; available: {labels}")
            checkpoint = matches[-1]
        else:
            matches = [item for item in available if item.seq == target]
            if not matches:
                seqs = ", ".join(str(item.seq) for item in available) or "none"
                raise ValueError(f"no checkpoint at seq {target} for task {task_id}; available: {seqs}")
            checkpoint = matches[0]
        return self.append(task_id, "rollback", {"target_seq": checkpoint.seq, "label": checkpoint.label})

    # -- queries ------------------------------------------------------------

    def list_tasks(self, *, status: str | None = None) -> list[TaskState]:
        states = [self.load(task_id) for task_id in self.task_ids()]
        if status is not None:
            states = [state for state in states if state.status == status]
        return sorted(states, key=lambda state: (state.created_at, state.task_id))

    # -- long-term (session-scoped) state (F-STATE-06) ----------------------

    def remember(self, session_id: str, key: str, value: Any) -> None:
        """Store a value that outlives one task but stays inside the session."""

        if not session_id:
            raise ValueError("session_id must be non-empty to store long-term state")
        safe_value = serialize_secret_refs(value)
        ensure_secret_refs({key: safe_value})
        data = self._read_session(session_id)
        data[key] = safe_value
        self._write_session(session_id, data)

    def recall(self, session_id: str, key: str | None = None, default: Any = None) -> Any:
        data = self._read_session(session_id)
        if key is None:
            return data
        return data.get(key, default)

    def forget(self, session_id: str, key: str | None = None) -> None:
        if key is None:
            self._write_session(session_id, {})
            return
        data = self._read_session(session_id)
        data.pop(key, None)
        self._write_session(session_id, data)


class InMemoryStateStore(StateStore):
    """Process-local store: fast, no persistence across restarts."""

    def __init__(self) -> None:
        super().__init__()
        self._events: dict[str, list[StateEvent]] = {}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def _read_events(self, task_id: str) -> list[StateEvent]:
        with self._lock:
            return list(self._events.get(task_id, ()))

    def _write_event(self, event: StateEvent) -> None:
        with self._lock:
            events = self._events.setdefault(event.task_id, [])
            if events and events[-1].seq >= event.seq:
                raise StateConflictError(
                    f"task {event.task_id} already has an event at seq {event.seq}; reload and retry"
                )
            events.append(event)

    def task_ids(self) -> list[str]:
        with self._lock:
            return sorted(self._events)

    def _read_session(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            return dict(self._sessions.get(session_id, {}))

    def _write_session(self, session_id: str, data: Mapping[str, Any]) -> None:
        with self._lock:
            self._sessions[session_id] = dict(data)


class JsonFileStateStore(StateStore):
    """One append-only JSONL event log per task under ``root`` (F-STATE-02)."""

    def __init__(self, root: str | Path) -> None:
        super().__init__()
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _task_path(self, task_id: str) -> Path:
        if not task_id or "/" in task_id or "\\" in task_id or task_id.startswith("."):
            raise ValueError(f"invalid task id for file storage: {task_id!r}")
        return self.root / f"{task_id}.jsonl"

    def _read_events(self, task_id: str) -> list[StateEvent]:
        path = self._task_path(task_id)
        if not path.exists():
            return []
        events: list[StateEvent] = []
        with path.open("r", encoding="utf-8") as file:
            for line_number, line in enumerate(file, start=1):
                if not line.strip():
                    continue
                try:
                    events.append(StateEvent.from_dict(json.loads(line)))
                except (json.JSONDecodeError, ValueError) as exc:
                    raise ValueError(f"invalid state event in {path} line {line_number}: {exc}") from exc
        return events

    def _write_event(self, event: StateEvent) -> None:
        path = self._task_path(event.task_id)
        with self._lock:
            existing = self._read_events(event.task_id)
            if existing and existing[-1].seq >= event.seq:
                raise StateConflictError(
                    f"task {event.task_id} already has an event at seq {event.seq}; reload and retry"
                )
            with path.open("a", encoding="utf-8") as file:
                json.dump(event.to_dict(), file, ensure_ascii=False, sort_keys=True, default=str)
                file.write("\n")

    def task_ids(self) -> list[str]:
        return sorted(path.stem for path in self.root.glob("*.jsonl"))

    def _session_path(self, session_id: str) -> Path:
        safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in session_id)
        directory = self.root / "sessions"
        directory.mkdir(parents=True, exist_ok=True)
        return directory / f"{safe}.json"

    def _read_session(self, session_id: str) -> dict[str, Any]:
        path = self._session_path(session_id)
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        values = data.get("values") if isinstance(data, Mapping) else None
        return dict(values) if isinstance(values, Mapping) else {}

    def _write_session(self, session_id: str, data: Mapping[str, Any]) -> None:
        payload = {"schema_version": SCHEMA_VERSION, "session_id": session_id, "values": dict(data)}
        self._session_path(session_id).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n",
            encoding="utf-8",
        )


class SQLiteStateStore(StateStore):
    """``sqlite3`` backend; the (task_id, seq) primary key enforces the lock."""

    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self.path = Path(path)
        if str(self.path) != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.path), check_same_thread=False)
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                task_id TEXT NOT NULL,
                seq INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                kind TEXT NOT NULL,
                payload TEXT NOT NULL,
                schema_version INTEGER NOT NULL,
                PRIMARY KEY (task_id, seq)
            );
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                values_json TEXT NOT NULL,
                schema_version INTEGER NOT NULL
            );
            """
        )
        self._connection.commit()
        self._lock = threading.Lock()

    def close(self) -> None:
        self._connection.close()

    def _read_events(self, task_id: str) -> list[StateEvent]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT task_id, seq, timestamp, kind, payload FROM events WHERE task_id = ? ORDER BY seq",
                (task_id,),
            ).fetchall()
        return [
            StateEvent(task_id=row[0], seq=row[1], timestamp=row[2], kind=row[3], payload=json.loads(row[4]))
            for row in rows
        ]

    def _write_event(self, event: StateEvent) -> None:
        payload = json.dumps(event.payload, ensure_ascii=False, sort_keys=True, default=str)
        with self._lock:
            try:
                self._connection.execute(
                    "INSERT INTO events (task_id, seq, timestamp, kind, payload, schema_version) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (event.task_id, event.seq, event.timestamp, event.kind, payload, SCHEMA_VERSION),
                )
                self._connection.commit()
            except sqlite3.IntegrityError as exc:
                raise StateConflictError(
                    f"task {event.task_id} already has an event at seq {event.seq}; reload and retry"
                ) from exc

    def task_ids(self) -> list[str]:
        with self._lock:
            rows = self._connection.execute("SELECT DISTINCT task_id FROM events ORDER BY task_id").fetchall()
        return [row[0] for row in rows]

    def _read_session(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            row = self._connection.execute(
                "SELECT values_json FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
        return dict(json.loads(row[0])) if row else {}

    def _write_session(self, session_id: str, data: Mapping[str, Any]) -> None:
        payload = json.dumps(dict(data), ensure_ascii=False, sort_keys=True, default=str)
        with self._lock:
            self._connection.execute(
                "INSERT INTO sessions (session_id, values_json, schema_version) VALUES (?, ?, ?) "
                "ON CONFLICT(session_id) DO UPDATE SET values_json = excluded.values_json",
                (session_id, payload, SCHEMA_VERSION),
            )
            self._connection.commit()


def _project(events: Iterable[StateEvent]) -> TaskState:
    """Fold an event sequence into the current state."""

    ordered = list(events)
    if not ordered:
        raise ValueError("cannot project an empty event sequence")
    first = ordered[0]
    if first.kind != "created":
        raise ValueError(f"first state event must be 'created', got {first.kind!r}")

    state = TaskState(
        task_id=first.task_id,
        goal=str(first.payload.get("goal", "")),
        session_id=str(first.payload.get("session_id", "")),
        version=first.seq,
        created_at=first.timestamp,
        updated_at=first.timestamp,
    )
    for index, event in enumerate(ordered[1:], start=1):
        if event.kind == "rollback":
            target = event.payload.get("target_seq")
            if not isinstance(target, int):
                raise ValueError(
                    f"rollback event {event.seq} target_seq must be an integer"
                )
            restored = _project([item for item in ordered[:index] if item.seq <= target])
            state = replace(restored, version=event.seq, updated_at=event.timestamp)
            continue
        state = replace(_apply(state, event), version=event.seq, updated_at=event.timestamp)
    return state


def _apply(state: TaskState, event: StateEvent) -> TaskState:
    payload = event.payload
    if event.kind == "status":
        return replace(
            state,
            status=str(payload.get("status", state.status)),
            detail=str(payload.get("detail", "")),
            output=str(payload.get("output", state.output)),
            trace_id=str(payload.get("trace_id", state.trace_id)),
            pending=None if payload.get("status") in TERMINAL_STATUSES else state.pending,
        )
    if event.kind == "variable":
        variables = dict(state.variables)
        variables[str(payload.get("key"))] = payload.get("value")
        return replace(state, variables=variables)
    if event.kind == "activated":
        resource = str(payload.get("resource", ""))
        if resource and resource not in state.activated:
            return replace(state, activated=state.activated + (resource,))
        return state
    if event.kind == "step":
        result = payload.get("result")
        if isinstance(result, Mapping):
            return replace(state, step_results=state.step_results + (dict(result),))
        return state
    if event.kind == "plan":
        plan = payload.get("plan")
        return replace(state, plan=dict(plan) if isinstance(plan, Mapping) else None)
    if event.kind == "frame":
        return replace(state, frame=dict(payload.get("frame") or {}))
    if event.kind == "paused":
        request = payload.get("request")
        return replace(
            state,
            status="escalated",
            detail=str(payload.get("detail", "")),
            pending=dict(request) if isinstance(request, Mapping) else None,
            frame=dict(payload.get("frame") or {}) or state.frame,
        )
    if event.kind == "resumed":
        return replace(
            state,
            status="running",
            pending=None,
            approvals=_merge(state.approvals, payload.get("approvals")),
            operation_approvals=_merge(
                state.operation_approvals, payload.get("operation_approvals")
            ),
            granted_permissions=_merge(state.granted_permissions, payload.get("granted_permissions")),
            frame=dict(payload.get("frame") or {}) if payload.get("frame") is not None else state.frame,
        )
    if event.kind == "checkpoint":
        return state
    return state


def _merge(existing: tuple[str, ...], addition: Any) -> tuple[str, ...]:
    """Append new string entries to ``existing``, preserving order and uniqueness."""

    merged = list(existing)
    if isinstance(addition, (list, tuple)):
        for item in addition:
            if str(item) not in merged:
                merged.append(str(item))
    return tuple(merged)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _required_str(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"state event {key} must be a non-empty string")
    return value
