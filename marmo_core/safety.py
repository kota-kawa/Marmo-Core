"""Argument-aware safety inspection for the execution gate (F-GATE-07)."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
import re
import shlex
from typing import Any, Iterable, Mapping
from urllib.parse import urlparse

from .models import ResourceDefinition
from .secrets import SENSITIVE_KEY_PARTS, SENSITIVE_VALUE_PATTERNS
SQL_DESTRUCTIVE = re.compile(
    r"\b(?:DROP\s+(?:DATABASE|SCHEMA|TABLE)|TRUNCATE\s+(?:TABLE\s+)?|DELETE\s+FROM\s+[^;]+)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SafetyFinding:
    """A redacted rule match suitable for policy decisions and audit logs."""

    code: str
    verdict: str  # deny / escalate
    message: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "verdict": self.verdict, "message": self.message}


class SafetyInspector:
    """Detect destructive commands and likely data exfiltration.

    The inspector deliberately returns only rule identifiers and redacted
    explanations. Argument values are used for matching and for the approval
    fingerprint, but never copied into a finding.
    """

    def inspect(
        self,
        resource: ResourceDefinition,
        arguments: Mapping[str, Any],
        *,
        allowed_external_hosts: Iterable[str] = (),
        blocked_external_hosts: Iterable[str] = (),
    ) -> tuple[SafetyFinding, ...]:
        findings: list[SafetyFinding] = []
        strings = tuple(_walk_strings(arguments))
        urls = tuple(_external_hosts(value) for _, value in strings)
        hosts = tuple(host for group in urls for host in group)
        allowed = tuple(_normalize_host(item) for item in allowed_external_hosts)
        blocked = tuple(_normalize_host(item) for item in blocked_external_hosts)

        blocked_matches = sorted({host for host in hosts if any(_host_matches(host, item) for item in blocked)})
        if blocked_matches:
            findings.append(
                SafetyFinding(
                    "external_host.blocked",
                    "deny",
                    "an external destination matches the configured blocklist",
                )
            )
        if allowed:
            outside = sorted({host for host in hosts if not any(_host_matches(host, item) for item in allowed)})
            if outside:
                findings.append(
                    SafetyFinding(
                        "external_host.not_allowed",
                        "deny",
                        "an external destination is outside the configured allowlist",
                    )
                )

        metadata = resource.metadata
        labels = {item.lower() for item in (*metadata.tags, *metadata.capabilities)}
        shell_like = "shell.exec" in metadata.required_permissions or any(
            marker in labels
            for marker in ("shell", "shell command", "os command")
        )
        database_like = any(
            permission.startswith(("db.", "database.", "sql."))
            for permission in metadata.required_permissions
        ) or any(marker in label for label in labels for marker in ("database", "sql", "sqlite"))
        if shell_like:
            for path, value in strings:
                if _argument_path_matches(path, ("cmd", "command", "commands", "script", "shell")):
                    findings.extend(_inspect_shell(value))
        elif database_like:
            for path, value in strings:
                if _argument_path_matches(path, ("cmd", "command", "query", "sql", "statement")):
                    finding = _inspect_destructive_sql(value)
                    if finding is not None:
                        findings.append(finding)

        sensitive = _contains_sensitive(arguments)
        externally_bound = metadata.side_effect in ("external", "irreversible") or bool(hosts)
        if sensitive and externally_bound:
            findings.append(
                SafetyFinding(
                    "data_exfiltration.sensitive_input",
                    "escalate",
                    "sensitive-looking input is being passed to an external operation",
                )
            )

        unique: dict[str, SafetyFinding] = {}
        for finding in findings:
            previous = unique.get(finding.code)
            if previous is None or (previous.verdict == "escalate" and finding.verdict == "deny"):
                unique[finding.code] = finding
        return tuple(unique[key] for key in sorted(unique))

    def approval_token(
        self,
        resource: ResourceDefinition,
        arguments: Mapping[str, Any],
        findings: Iterable[SafetyFinding],
    ) -> str:
        """Fingerprint the exact reviewed call without exposing its arguments."""

        payload = {
            "resource": resource.metadata.identity,
            "arguments": arguments,
            "findings": sorted(finding.code for finding in findings),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
        return "operation:" + sha256(encoded).hexdigest()


def redact_sensitive_arguments(value: Any, path: tuple[str, ...] = ()) -> Any:
    """Redact sensitive keys and credential-shaped values for HITL display."""

    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, nested in value.items():
            key_string = str(key)
            normalized = key_string.lower().replace("-", "_")
            if any(part in normalized for part in SENSITIVE_KEY_PARTS):
                redacted[key_string] = "[REDACTED]"
            else:
                redacted[key_string] = redact_sensitive_arguments(nested, (*path, key_string))
        return redacted
    if isinstance(value, (list, tuple)):
        return [redact_sensitive_arguments(item, (*path, str(index))) for index, item in enumerate(value)]
    if isinstance(value, str) and any(pattern.search(value) for pattern in SENSITIVE_VALUE_PATTERNS):
        return "[REDACTED]"
    return value


def _walk_strings(value: Any, path: tuple[str, ...] = ()) -> Iterable[tuple[tuple[str, ...], str]]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            yield from _walk_strings(nested, (*path, str(key)))
    elif isinstance(value, (list, tuple)):
        for index, nested in enumerate(value):
            yield from _walk_strings(nested, (*path, str(index)))
    elif isinstance(value, str):
        yield path, value


def _contains_sensitive(arguments: Mapping[str, Any]) -> bool:
    for path, value in _walk_strings(arguments):
        normalized = "_".join(path).lower().replace("-", "_")
        if any(part in normalized for part in SENSITIVE_KEY_PARTS):
            return True
        if any(pattern.search(value) for pattern in SENSITIVE_VALUE_PATTERNS):
            return True
    return False


def _argument_path_matches(path: tuple[str, ...], names: tuple[str, ...]) -> bool:
    normalized = {item.lower().replace("-", "_") for item in path if not item.isdigit()}
    return bool(normalized & set(names))


def _external_hosts(value: str) -> tuple[str, ...]:
    hosts: list[str] = []
    for match in re.finditer(r"https?://[^\s'\"<>]+", value, re.IGNORECASE):
        host = urlparse(match.group(0)).hostname
        if host:
            hosts.append(host.lower().rstrip("."))
    return tuple(hosts)


def _normalize_host(value: str) -> str:
    normalized = value.strip().lower().rstrip(".")
    return normalized[2:] if normalized.startswith("*.") else normalized


def _host_matches(host: str, configured: str) -> bool:
    return host == configured or host.endswith("." + configured)


def _inspect_shell(command: str) -> list[SafetyFinding]:
    findings: list[SafetyFinding] = []
    lowered = command.lower()
    if ":(){:|:&};:" in command.replace(" ", ""):
        findings.append(SafetyFinding("shell.fork_bomb", "deny", "a process-spawning fork bomb was detected"))
    if re.search(r"(?:^|[;&|]\s*)(?:sudo\s+)?mkfs(?:\.|\s)", lowered):
        findings.append(SafetyFinding("shell.format_device", "deny", "a filesystem formatting command was detected"))
    if re.search(r"\bdd\b[^\n;&|]*\bof\s*=\s*/dev/", lowered):
        findings.append(SafetyFinding("shell.raw_device_write", "deny", "a raw device write was detected"))

    for segment in re.split(r"(?:&&|\|\||[;|\n])", command):
        try:
            tokens = shlex.split(segment, comments=True, posix=True)
        except ValueError:
            tokens = segment.split()
        if tokens and tokens[0] == "sudo":
            dangerous = {"dd", "git", "halt", "mkfs", "poweroff", "reboot", "rm", "shutdown"}
            command_index = next(
                (
                    index
                    for index, token in enumerate(tokens[1:], start=1)
                    if token.rsplit("/", 1)[-1].lower() in dangerous
                ),
                len(tokens),
            )
            tokens = tokens[command_index:]
        if not tokens:
            continue
        executable = tokens[0].rsplit("/", 1)[-1].lower()
        if executable == "rm":
            flags = "".join(token[1:] for token in tokens[1:] if token.startswith("-") and token != "--")
            targets = [token for token in tokens[1:] if not token.startswith("-")]
            if "r" in flags and "f" in flags:
                roots = {"/", "/*", "~", "~/", "$HOME", "${HOME}"}
                verdict = "deny" if any(target in roots for target in targets) else "escalate"
                code = "shell.root_delete" if verdict == "deny" else "shell.recursive_delete"
                message = (
                    "recursive forced deletion targets a broad protected location"
                    if verdict == "deny"
                    else "recursive forced deletion was detected"
                )
                findings.append(SafetyFinding(code, verdict, message))
        if executable in ("shutdown", "reboot", "poweroff", "halt"):
            findings.append(SafetyFinding("shell.host_shutdown", "escalate", "a host shutdown command was detected"))
        if executable == "git" and len(tokens) >= 2:
            if tokens[1].lower() == "push" and any(token in ("-f", "--force", "--force-with-lease") for token in tokens[2:]):
                findings.append(SafetyFinding("shell.force_push", "escalate", "a forced Git push was detected"))
            if tokens[1].lower() == "reset" and "--hard" in tokens[2:]:
                findings.append(SafetyFinding("shell.hard_reset", "escalate", "a hard Git reset was detected"))

    sql_finding = _inspect_destructive_sql(command)
    if sql_finding is not None:
        findings.append(sql_finding)
    return findings


def _inspect_destructive_sql(statement: str) -> SafetyFinding | None:
    sql_match = SQL_DESTRUCTIVE.search(statement)
    if sql_match:
        matched = sql_match.group(0).upper()
        if matched.startswith("DELETE") and re.search(r"\bWHERE\b", matched):
            return None
        return SafetyFinding(
            "database.destructive_statement",
            "escalate",
            "a destructive database statement was detected",
        )
    return None
