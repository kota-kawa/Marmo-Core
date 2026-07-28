"""Zero-dependency Connector API and built-in connectors (F-CONN-01..06).

Connectors expose external operations as ordinary Tool resources.  This keeps
one mandatory security path: the Kernel activates their definitions through
the Policy Gateway and executes their handlers through ToolRuntime.  The
connector layer adds operation-local rate limits, retry budgets, and a circuit
breaker, while the Kernel's Recovery Manager remains responsible for workflow
level recovery.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import monotonic, sleep
from typing import Any, Callable, Iterable, Mapping, Sequence
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
import base64
import ipaddress
import os
import shlex
import shutil
import socket
import sqlite3
import subprocess
import tempfile

from .errors import MarmoError, ResourceNotFoundError, ResourceValidationError
from .models import ResourceDefinition
from .registry import ResourceRegistry


class ConnectorError(MarmoError):
    """Base error raised by a Connector handler."""


class ConnectorCircuitOpenError(ConnectorError):
    """The operation is blocked after repeated Connector failures."""


class ConnectorPathError(ConnectorError):
    """A requested path escaped its configured Connector root."""


class ConnectorCommandError(ConnectorError):
    """A shell command exited unsuccessfully."""


@dataclass(frozen=True)
class ConnectorConfig:
    """Connector-local resilience controls (F-CONN-05)."""

    timeout_seconds: float = 30.0
    max_attempts: int = 1
    initial_backoff_seconds: float = 0.1
    backoff_multiplier: float = 2.0
    rate_limit_per_second: float | None = None
    circuit_failure_threshold: int = 3
    circuit_reset_seconds: float = 60.0

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_backoff_seconds < 0 or self.backoff_multiplier < 1:
            raise ValueError("backoff values must be non-negative and multiplier must be at least 1")
        if self.rate_limit_per_second is not None and self.rate_limit_per_second <= 0:
            raise ValueError("rate_limit_per_second must be positive or None")
        if self.circuit_failure_threshold < 1:
            raise ValueError("circuit_failure_threshold must be at least 1")
        if self.circuit_reset_seconds < 0:
            raise ValueError("circuit_reset_seconds must be non-negative")


@dataclass(frozen=True)
class ConnectorTool:
    """One Connector operation exposed to Registry and ToolRuntime."""

    connector_id: str
    operation: str
    definition: ResourceDefinition
    handler: Callable[..., Any]

    @property
    def resource_id(self) -> str:
        return self.definition.metadata.id


class ConnectorRuntime:
    """Rate-limit and recover individual Connector operations."""

    def __init__(
        self,
        config: ConnectorConfig | None = None,
        *,
        retry_exceptions: tuple[type[BaseException], ...] = (OSError, TimeoutError),
        clock: Callable[[], float] = monotonic,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self.config = config or ConnectorConfig()
        self.retry_exceptions = retry_exceptions
        self._clock = clock
        self._sleep = sleeper
        self._lock = Lock()
        self._failures: dict[str, int] = {}
        self._opened_at: dict[str, float] = {}
        self._next_allowed_at: dict[str, float] = {}

    def execute(
        self,
        resource_id: str,
        handler: Callable[..., Any],
        arguments: Mapping[str, Any],
        *,
        retry_safe: bool,
    ) -> Any:
        self._wait_for_rate_limit(resource_id)
        self._check_circuit(resource_id)
        attempts = self.config.max_attempts if retry_safe else 1
        for attempt in range(attempts):
            try:
                output = handler(**dict(arguments))
            except self.retry_exceptions:
                self._record_failure(resource_id)
                if attempt + 1 >= attempts or self._circuit_is_open(resource_id):
                    raise
                delay = self.config.initial_backoff_seconds * (
                    self.config.backoff_multiplier**attempt
                )
                if delay:
                    self._sleep(delay)
            except Exception:
                # Invalid input and policy-shaped Connector errors should not
                # make a healthy endpoint look unavailable.
                raise
            else:
                self._record_success(resource_id)
                return output
        raise AssertionError("connector retry loop ended without a result")

    def wrap(
        self,
        resource_id: str,
        handler: Callable[..., Any],
        *,
        retry_safe: bool,
    ) -> Callable[..., Any]:
        def guarded(**arguments: Any) -> Any:
            return self.execute(resource_id, handler, arguments, retry_safe=retry_safe)

        return guarded

    def _wait_for_rate_limit(self, resource_id: str) -> None:
        rate = self.config.rate_limit_per_second
        if rate is None:
            return
        interval = 1.0 / rate
        with self._lock:
            now = self._clock()
            scheduled = max(now, self._next_allowed_at.get(resource_id, now))
            self._next_allowed_at[resource_id] = scheduled + interval
        delay = scheduled - now
        if delay > 0:
            self._sleep(delay)

    def _check_circuit(self, resource_id: str) -> None:
        with self._lock:
            opened = self._opened_at.get(resource_id)
            if opened is None:
                return
            if self._clock() - opened >= self.config.circuit_reset_seconds:
                self._opened_at.pop(resource_id, None)
                self._failures[resource_id] = 0
                return
        raise ConnectorCircuitOpenError(
            f"connector circuit is open for {resource_id}; wait for the reset interval or fix the endpoint"
        )

    def _circuit_is_open(self, resource_id: str) -> bool:
        with self._lock:
            return resource_id in self._opened_at

    def _record_failure(self, resource_id: str) -> None:
        with self._lock:
            failures = self._failures.get(resource_id, 0) + 1
            self._failures[resource_id] = failures
            if failures >= self.config.circuit_failure_threshold:
                self._opened_at[resource_id] = self._clock()

    def _record_success(self, resource_id: str) -> None:
        with self._lock:
            self._failures.pop(resource_id, None)
            self._opened_at.pop(resource_id, None)


class Connector(ABC):
    """Pluggable source of Tool resources backed by an external environment."""

    def __init__(
        self,
        connector_id: str,
        *,
        config: ConnectorConfig | None = None,
        retry_exceptions: tuple[type[BaseException], ...] = (OSError, TimeoutError),
    ) -> None:
        if not connector_id.strip():
            raise ValueError("connector_id must be non-empty")
        self.connector_id = connector_id.strip()
        self.config = config or ConnectorConfig()
        self.runtime = ConnectorRuntime(self.config, retry_exceptions=retry_exceptions)

    @abstractmethod
    def tools(self) -> tuple[ConnectorTool, ...]:
        """Return the operations this Connector contributes to the Registry."""

    def _bind(
        self,
        operation: str,
        handler: Callable[..., Any],
        *,
        name: str,
        description: str,
        capabilities: Sequence[str],
        input_summary: str,
        output_summary: str,
        required_permissions: Sequence[str],
        side_effect: str,
        isolation_level: str,
        input_schema: Mapping[str, Any],
        output_schema: Mapping[str, Any] | None = None,
        retry_safe: bool = False,
        cost_estimate: float = 0.0,
        latency_class: str = "fast",
        tags: Sequence[str] = (),
    ) -> ConnectorTool:
        resource_id = f"{self.connector_id}.{operation}"
        definition = ResourceDefinition.from_mapping(
            {
                "id": resource_id,
                "kind": "tool",
                "name": name,
                "version": "1.0.0",
                "description": description,
                "capabilities": list(capabilities),
                "input_summary": input_summary,
                "output_summary": output_summary,
                "required_permissions": list(required_permissions),
                "cost_estimate": cost_estimate,
                "latency_class": latency_class,
                "side_effect": side_effect,
                "trust_level": "core",
                "ref": f"connector:{self.connector_id}:{operation}",
                "tags": ["connector", self.connector_id, *tags],
                "input_schema": dict(input_schema),
                "output_schema": dict(output_schema or {}),
                "isolation_level": isolation_level,
                "connector": {
                    "id": self.connector_id,
                    "operation": operation,
                    "timeout_seconds": self.config.timeout_seconds,
                },
            }
        )
        issues = definition.validate()
        if issues:
            raise ResourceValidationError(
                "; ".join(f"{issue.path}: {issue.message}" for issue in issues)
            )
        return ConnectorTool(
            connector_id=self.connector_id,
            operation=operation,
            definition=definition,
            handler=self.runtime.wrap(resource_id, handler, retry_safe=retry_safe),
        )


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> None:
        return None


class HTTPConnector(Connector):
    """HTTP/HTTPS connector with no redirects and private-network denial."""

    def __init__(
        self,
        connector_id: str = "connector.http",
        *,
        config: ConnectorConfig | None = None,
        allowed_methods: Sequence[str] = ("GET", "HEAD", "POST"),
        allowed_hosts: Sequence[str] = (),
        max_response_bytes: int = 1_000_000,
        allow_private_networks: bool = False,
    ) -> None:
        super().__init__(connector_id, config=config)
        methods = tuple(dict.fromkeys(item.upper() for item in allowed_methods))
        if not methods:
            raise ValueError("allowed_methods must not be empty")
        if max_response_bytes < 1:
            raise ValueError("max_response_bytes must be positive")
        self.allowed_methods = methods
        self.allowed_hosts = tuple(_normalize_host(item) for item in allowed_hosts if item.strip())
        self.max_response_bytes = max_response_bytes
        self.allow_private_networks = allow_private_networks
        self._opener = build_opener(_NoRedirect())

    def tools(self) -> tuple[ConnectorTool, ...]:
        return (
            self._bind(
                "request",
                self._request,
                name="HTTP request",
                description="Send one bounded HTTP/HTTPS request without following redirects.",
                capabilities=("http", "rest api", "network request"),
                input_summary="URL, method, headers, and optional UTF-8 body",
                output_summary="status, response headers, and bounded response text",
                required_permissions=("connector.http.request",),
                side_effect="external",
                isolation_level="L2" if self.allowed_hosts else "L1",
                input_schema={
                    "type": "object",
                    "required": ["url"],
                    "properties": {
                        "url": {"type": "string"},
                        "method": {"type": "string", "enum": list(self.allowed_methods), "default": "GET"},
                        "headers": {"type": "object", "default": {}},
                        "body": {"type": "string"},
                    },
                    "additionalProperties": False,
                },
                retry_safe=False,
                latency_class="medium",
                tags=("http", "network"),
            ),
        )

    def _request(
        self,
        url: str,
        method: str = "GET",
        headers: Mapping[str, Any] | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ConnectorError("HTTP URL must use http or https and include a hostname")
        if parsed.username is not None or parsed.password is not None:
            raise ConnectorError("credentials in URLs are forbidden; use SecretRef-backed headers")
        hostname = parsed.hostname.lower().rstrip(".")
        if self.allowed_hosts and not any(
            _host_matches(hostname, configured) for configured in self.allowed_hosts
        ):
            raise ConnectorError("HTTP destination is outside the Connector host allowlist")
        method = method.upper()
        if method not in self.allowed_methods:
            raise ConnectorError(f"HTTP method {method} is not allowed")
        if not self.allow_private_networks:
            _deny_private_destination(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
        clean_headers: dict[str, str] = {}
        for key, value in (headers or {}).items():
            if not isinstance(key, str) or not isinstance(value, str):
                raise ConnectorError("HTTP headers must map strings to strings")
            clean_headers[key] = value
        data = body.encode("utf-8") if body is not None else None
        request = Request(url, data=data, headers=clean_headers, method=method)
        try:
            response = self._opener.open(request, timeout=self.config.timeout_seconds)
        except HTTPError as exc:
            status = exc.code
            exc.close()
            if status in (408, 425, 429) or status >= 500:
                raise OSError(f"transient HTTP request failure with status {status}") from exc
            raise ConnectorError(f"HTTP request failed with status {status}") from exc
        with response:
            payload = response.read(self.max_response_bytes + 1)
            if len(payload) > self.max_response_bytes:
                raise ConnectorError(
                    f"HTTP response exceeds max_response_bytes={self.max_response_bytes}"
                )
            response_headers = {
                key: value
                for key, value in response.headers.items()
                if key.lower() not in ("authorization", "proxy-authorization", "set-cookie")
            }
            charset = response.headers.get_content_charset() or "utf-8"
            return {
                "status": int(response.status),
                "url": response.geturl(),
                "headers": response_headers,
                "body": payload.decode(charset, errors="replace"),
            }


class FileSystemConnector(Connector):
    """UTF-8 file operations confined beneath one resolved root directory."""

    def __init__(
        self,
        root: str | Path,
        connector_id: str = "connector.file",
        *,
        config: ConnectorConfig | None = None,
        max_read_bytes: int = 1_000_000,
        max_list_entries: int = 1_000,
    ) -> None:
        super().__init__(connector_id, config=config)
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError(f"file connector root is not a directory: {self.root}")
        if max_read_bytes < 1 or max_list_entries < 1:
            raise ValueError("file connector limits must be positive")
        self.max_read_bytes = max_read_bytes
        self.max_list_entries = max_list_entries

    def tools(self) -> tuple[ConnectorTool, ...]:
        path_schema = {"type": "string"}
        return (
            self._bind(
                "read_text",
                self._read_text,
                name="Read text file",
                description="Read one bounded UTF-8 file beneath the configured root.",
                capabilities=("file read", "filesystem"),
                input_summary="root-relative file path",
                output_summary="file path and UTF-8 text",
                required_permissions=("connector.file.read",),
                side_effect="read",
                isolation_level="L2",
                input_schema={
                    "type": "object",
                    "required": ["path"],
                    "properties": {"path": path_schema},
                    "additionalProperties": False,
                },
                retry_safe=True,
                tags=("file", "filesystem"),
            ),
            self._bind(
                "list",
                self._list,
                name="List directory",
                description="List one directory beneath the configured root without recursion.",
                capabilities=("file list", "filesystem"),
                input_summary="optional root-relative directory path",
                output_summary="bounded list of child entries",
                required_permissions=("connector.file.read",),
                side_effect="read",
                isolation_level="L2",
                input_schema={
                    "type": "object",
                    "properties": {"path": {"type": "string", "default": "."}},
                    "additionalProperties": False,
                },
                retry_safe=True,
                tags=("file", "filesystem"),
            ),
            self._bind(
                "write_text",
                self._write_text,
                name="Write text file",
                description="Atomically replace one UTF-8 file beneath the configured root.",
                capabilities=("file write", "filesystem"),
                input_summary="root-relative path and UTF-8 text",
                output_summary="written path and byte count",
                required_permissions=("connector.file.write",),
                side_effect="write",
                isolation_level="L2",
                input_schema={
                    "type": "object",
                    "required": ["path", "text"],
                    "properties": {"path": path_schema, "text": {"type": "string"}},
                    "additionalProperties": False,
                },
                retry_safe=False,
                tags=("file", "filesystem"),
            ),
        )

    def _resolve(self, raw_path: str, *, require_exists: bool = True) -> Path:
        relative = Path(raw_path)
        if relative.is_absolute():
            raise ConnectorPathError("file paths must be relative to the configured root")
        candidate = (self.root / relative).resolve(strict=False)
        if not candidate.is_relative_to(self.root):
            raise ConnectorPathError("file path escapes the configured root")
        if require_exists and not candidate.exists():
            raise ConnectorPathError(f"file path does not exist beneath the configured root: {raw_path}")
        return candidate

    def _read_text(self, path: str) -> dict[str, Any]:
        target = self._resolve(path)
        if not target.is_file():
            raise ConnectorPathError(f"file path is not a regular file: {path}")
        size = target.stat().st_size
        if size > self.max_read_bytes:
            raise ConnectorError(f"file exceeds max_read_bytes={self.max_read_bytes}")
        return {"path": target.relative_to(self.root).as_posix(), "text": target.read_text("utf-8")}

    def _list(self, path: str = ".") -> dict[str, Any]:
        target = self._resolve(path)
        if not target.is_dir():
            raise ConnectorPathError(f"file path is not a directory: {path}")
        children = sorted(target.iterdir(), key=lambda item: item.name)
        truncated = len(children) > self.max_list_entries
        entries = [
            {
                "name": child.name,
                "type": (
                    "symlink"
                    if child.is_symlink()
                    else "directory"
                    if child.is_dir()
                    else "file"
                    if child.is_file()
                    else "other"
                ),
            }
            for child in children[: self.max_list_entries]
        ]
        return {
            "path": target.relative_to(self.root).as_posix() or ".",
            "entries": entries,
            "truncated": truncated,
        }

    def _write_text(self, path: str, text: str) -> dict[str, Any]:
        target = self._resolve(path, require_exists=False)
        if not target.parent.is_dir():
            raise ConnectorPathError("parent directory must already exist beneath the configured root")
        if target.exists() and not target.is_file():
            raise ConnectorPathError(f"file path is not a regular file: {path}")
        encoded = text.encode("utf-8")
        if len(encoded) > self.max_read_bytes:
            raise ConnectorError(f"text exceeds max_read_bytes={self.max_read_bytes}")
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{target.name}.marmo-",
            suffix=".tmp",
            dir=target.parent,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(encoded)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
        return {"path": target.relative_to(self.root).as_posix(), "bytes_written": len(encoded)}


class ShellConnector(Connector):
    """Allowlisted argv execution using ``shell=False`` inside one cwd root."""

    def __init__(
        self,
        root: str | Path,
        allowed_commands: Sequence[str],
        connector_id: str = "connector.shell",
        *,
        config: ConnectorConfig | None = None,
        allowed_environment: Sequence[str] = ("PATH",),
        max_output_bytes: int = 1_000_000,
    ) -> None:
        super().__init__(connector_id, config=config)
        self.root = Path(root).resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError(f"shell connector root is not a directory: {self.root}")
        if not allowed_commands:
            raise ValueError("allowed_commands must contain at least one executable")
        resolved: set[Path] = set()
        for command in allowed_commands:
            found = shutil.which(command)
            if found is None:
                raise ValueError(f"allowed shell command was not found: {command}")
            resolved.add(Path(found).resolve(strict=True))
        if max_output_bytes < 1:
            raise ValueError("max_output_bytes must be positive")
        self.allowed_commands = frozenset(resolved)
        self.allowed_environment = frozenset(allowed_environment)
        self.max_output_bytes = max_output_bytes

    def tools(self) -> tuple[ConnectorTool, ...]:
        return (
            self._bind(
                "run",
                self._run,
                name="Run allowlisted command",
                description="Run one allowlisted command with shell expansion disabled.",
                capabilities=("shell", "os command", "subprocess"),
                input_summary="quoted command string, optional cwd and allowlisted environment",
                output_summary="exit code and bounded stdout/stderr",
                required_permissions=("shell.exec",),
                side_effect="irreversible",
                isolation_level="L1",
                input_schema={
                    "type": "object",
                    "required": ["command"],
                    "properties": {
                        "command": {"type": "string"},
                        "cwd": {"type": "string", "default": "."},
                        "env": {"type": "object", "default": {}},
                    },
                    "additionalProperties": False,
                },
                retry_safe=False,
                latency_class="medium",
                tags=("shell", "os command"),
            ),
        )

    def _run(
        self,
        command: str,
        cwd: str = ".",
        env: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            argv = shlex.split(command, comments=False, posix=True)
        except ValueError as exc:
            raise ConnectorCommandError(f"invalid command quoting: {exc}") from exc
        if not argv:
            raise ConnectorCommandError("command must not be empty")
        executable = shutil.which(argv[0])
        if executable is None or Path(executable).resolve(strict=True) not in self.allowed_commands:
            raise ConnectorCommandError("command executable is not in the Connector allowlist")
        working = (self.root / cwd).resolve(strict=False)
        if Path(cwd).is_absolute() or not working.is_relative_to(self.root) or not working.is_dir():
            raise ConnectorPathError("shell cwd must be an existing directory beneath the configured root")
        environment = {
            key: value for key, value in os.environ.items() if key in self.allowed_environment
        }
        for key, value in (env or {}).items():
            if key not in self.allowed_environment or not isinstance(value, str):
                raise ConnectorCommandError(
                    "shell env may only contain configured string-valued environment keys"
                )
            environment[key] = value
        completed = subprocess.run(
            [str(Path(executable).resolve(strict=True)), *argv[1:]],
            cwd=working,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=self.config.timeout_seconds,
            check=False,
        )
        stdout = completed.stdout[: self.max_output_bytes].decode("utf-8", errors="replace")
        stderr = completed.stderr[: self.max_output_bytes].decode("utf-8", errors="replace")
        if completed.returncode != 0:
            raise ConnectorCommandError(
                f"command exited with status {completed.returncode}: {stderr[:500]}"
            )
        return {
            "exit_code": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "stdout_truncated": len(completed.stdout) > self.max_output_bytes,
            "stderr_truncated": len(completed.stderr) > self.max_output_bytes,
        }


class SQLiteConnector(Connector):
    """Parameterized read/write tools for one fixed SQLite database."""

    _WRITE_VERBS = frozenset(("INSERT", "UPDATE", "DELETE", "CREATE", "ALTER", "DROP", "REPLACE"))

    def __init__(
        self,
        database: str | Path,
        connector_id: str = "connector.sqlite",
        *,
        config: ConnectorConfig | None = None,
        max_rows: int = 1_000,
    ) -> None:
        super().__init__(
            connector_id,
            config=config,
            retry_exceptions=(sqlite3.OperationalError, OSError, TimeoutError),
        )
        self.database = Path(database).resolve(strict=False)
        if not self.database.parent.is_dir():
            raise ValueError(f"SQLite parent directory does not exist: {self.database.parent}")
        if max_rows < 1:
            raise ValueError("max_rows must be positive")
        self.max_rows = max_rows

    def tools(self) -> tuple[ConnectorTool, ...]:
        parameter_schema = {"type": "object", "default": {}}
        return (
            self._bind(
                "query",
                self._query,
                name="Query SQLite",
                description="Run one parameterized read-only query against the configured SQLite database.",
                capabilities=("sqlite", "database", "sql query"),
                input_summary="read-only SQL, named parameters, and optional row limit",
                output_summary="columns and bounded JSON-compatible rows",
                required_permissions=("connector.sqlite.read",),
                side_effect="read",
                isolation_level="L2",
                input_schema={
                    "type": "object",
                    "required": ["sql"],
                    "properties": {
                        "sql": {"type": "string"},
                        "parameters": parameter_schema,
                        "limit": {"type": "integer", "minimum": 1, "maximum": self.max_rows, "default": self.max_rows},
                    },
                    "additionalProperties": False,
                },
                retry_safe=True,
                latency_class="medium",
                tags=("sqlite", "database", "sql"),
            ),
            self._bind(
                "execute",
                self._execute,
                name="Execute SQLite statement",
                description="Run one parameterized write or schema statement against the configured database.",
                capabilities=("sqlite", "database", "sql execute"),
                input_summary="single write SQL statement and named parameters",
                output_summary="affected row count and inserted row id",
                required_permissions=("connector.sqlite.write",),
                side_effect="write",
                isolation_level="L2",
                input_schema={
                    "type": "object",
                    "required": ["sql"],
                    "properties": {"sql": {"type": "string"}, "parameters": parameter_schema},
                    "additionalProperties": False,
                },
                retry_safe=False,
                latency_class="medium",
                tags=("sqlite", "database", "sql"),
            ),
        )

    def _query(
        self,
        sql: str,
        parameters: Mapping[str, Any] | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        stripped = sql.lstrip()
        verb = stripped.split(None, 1)[0].upper() if stripped else ""
        if verb not in ("SELECT", "WITH", "EXPLAIN"):
            raise ConnectorError("SQLite query accepts only SELECT, WITH, or EXPLAIN statements")
        row_limit = self.max_rows if limit is None else min(limit, self.max_rows)
        database = self._checked_database()
        uri = f"{database.as_uri()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=self.config.timeout_seconds) as connection:
            cursor = connection.execute(sql, dict(parameters or {}))
            if cursor.description is None:
                raise ConnectorError("SQLite query must produce rows; use the execute operation for writes")
            rows = cursor.fetchmany(row_limit + 1)
            columns = [item[0] for item in cursor.description]
        return {
            "columns": columns,
            "rows": [[_json_value(value) for value in row] for row in rows[:row_limit]],
            "truncated": len(rows) > row_limit,
        }

    def _execute(
        self,
        sql: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        stripped = sql.lstrip()
        verb = stripped.split(None, 1)[0].upper() if stripped else ""
        if verb not in self._WRITE_VERBS:
            raise ConnectorError(
                "SQLite execute accepts one INSERT/UPDATE/DELETE/CREATE/ALTER/DROP/REPLACE statement"
            )
        database = self._checked_database()
        with sqlite3.connect(database, timeout=self.config.timeout_seconds) as connection:
            cursor = connection.execute(sql, dict(parameters or {}))
            connection.commit()
            return {"rowcount": cursor.rowcount, "lastrowid": cursor.lastrowid}

    def _checked_database(self) -> Path:
        current = self.database.resolve(strict=False)
        if current != self.database:
            raise ConnectorPathError("SQLite database path changed through a symlink")
        return current


def connector_tools(connectors: Iterable[Connector]) -> tuple[ConnectorTool, ...]:
    """Flatten Connector plugins and reject duplicate Tool identities."""

    tools: list[ConnectorTool] = []
    identities: set[str] = set()
    for connector in connectors:
        for tool in connector.tools():
            identity = tool.definition.identity
            if identity in identities:
                raise ResourceValidationError(f"duplicate Connector Tool identity: {identity}")
            identities.add(identity)
            tools.append(tool)
    return tuple(tools)


def connector_resources(connectors: Iterable[Connector]) -> tuple[ResourceDefinition, ...]:
    return tuple(tool.definition for tool in connector_tools(connectors))


def connector_implementations(connectors: Iterable[Connector]) -> dict[str, Callable[..., Any]]:
    return {tool.resource_id: tool.handler for tool in connector_tools(connectors)}


def install_connectors(
    registry: ResourceRegistry,
    connectors: Iterable[Connector],
) -> dict[str, Callable[..., Any]]:
    """Install Connector Tool definitions and return Activator handlers."""

    tools = connector_tools(connectors)
    for tool in tools:
        try:
            registry.get(tool.definition.metadata.id, tool.definition.metadata.version)
        except ResourceNotFoundError:
            pass
        else:
            raise ResourceValidationError(
                f"Connector Tool is already registered: {tool.definition.identity}"
            )
    for tool in tools:
        registry.add(tool.definition)
    return {tool.resource_id: tool.handler for tool in tools}


def _deny_private_destination(hostname: str, port: int) -> None:
    try:
        addresses = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ConnectorError(f"HTTP hostname could not be resolved: {hostname}") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ConnectorError(
                "HTTP destination resolves to a private, loopback, link-local, or reserved address"
            )


def _normalize_host(value: str) -> str:
    normalized = value.strip().lower().rstrip(".")
    return normalized[2:] if normalized.startswith("*.") else normalized


def _host_matches(host: str, configured: str) -> bool:
    return host == configured or host.endswith("." + configured)


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, bytes):
        return {"base64": base64.b64encode(value).decode("ascii")}
    return str(value)
