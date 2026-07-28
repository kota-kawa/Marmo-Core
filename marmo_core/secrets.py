"""Opaque secret references resolved only at the Tool Runtime boundary.

Plans, LLM messages, and persisted state carry ``SecretRef`` markers instead
of credential values; audit records redact the reference name as well. A
resolver materializes markers only after a resource-level policy preflight and
immediately before argument safety inspection, schema validation, and handler
execution.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Mapping
import os
import re

from .errors import SecretResolutionError


SECRET_REF_KEY = "$secret"
SENSITIVE_KEY_PARTS = (
    "api_key",
    "apikey",
    "authorization",
    "credential",
    "password",
    "private_key",
    "secret",
    "token",
)
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"-----BEGIN (?:[A-Z ]+ )?PRIVATE KEY-----"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\b(?:gh[opusr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,})\b"),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
)
NON_SECRET_TOKEN_KEYS = {
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
class SecretRef:
    """A serializable reference to a secret held outside kernel state."""

    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("secret reference name must be a non-empty string")

    def to_dict(self) -> dict[str, str]:
        return {SECRET_REF_KEY: self.name}

    def __repr__(self) -> str:
        return f"SecretRef({self.name!r})"


class SecretResolver(ABC):
    """Resolve a named secret without exposing the backing store to the kernel."""

    @abstractmethod
    def resolve(self, reference: SecretRef) -> Any:
        """Return the secret value or raise ``SecretResolutionError``."""


class MappingSecretResolver(SecretResolver):
    """Resolver for applications, tests, and injected secret managers."""

    def __init__(self, values: Mapping[str, Any]) -> None:
        self._values = dict(values)

    def resolve(self, reference: SecretRef) -> Any:
        if reference.name not in self._values:
            raise SecretResolutionError(
                f"secret reference {reference.name!r} was not found; add it to the configured resolver"
            )
        return self._values[reference.name]


class EnvironmentSecretResolver(SecretResolver):
    """Resolve references from environment variables, optionally with a prefix."""

    def __init__(self, *, prefix: str = "") -> None:
        self.prefix = prefix

    def resolve(self, reference: SecretRef) -> str:
        variable = f"{self.prefix}{reference.name}"
        if variable not in os.environ:
            raise SecretResolutionError(
                f"secret reference {reference.name!r} was not found in environment variable {variable!r}"
            )
        return os.environ[variable]


def is_secret_ref(value: Any) -> bool:
    """Whether ``value`` is a SecretRef object or its JSON marker."""

    return isinstance(value, SecretRef) or (
        isinstance(value, Mapping)
        and set(value) == {SECRET_REF_KEY}
        and isinstance(value.get(SECRET_REF_KEY), str)
        and bool(value[SECRET_REF_KEY].strip())
    )


def serialize_secret_refs(value: Any) -> Any:
    """Return a JSON-friendly tree containing references, never secret values."""

    if isinstance(value, SecretRef):
        return value.to_dict()
    if isinstance(value, Mapping):
        return {str(key): serialize_secret_refs(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [serialize_secret_refs(item) for item in value]
    return value


def plaintext_secret_paths(value: Any, path: tuple[str, ...] = ()) -> tuple[str, ...]:
    """Locate credential-shaped plaintext that must be replaced by SecretRef."""

    if is_secret_ref(value):
        return ()
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            key_string = str(key)
            normalized = key_string.casefold().replace("-", "_")
            item_path = (*path, key_string)
            if _is_sensitive_key(normalized) and _contains_material(item):
                found.append(".".join(item_path))
                continue
            found.extend(plaintext_secret_paths(item, item_path))
    elif isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            found.extend(plaintext_secret_paths(item, (*path, str(index))))
    elif isinstance(value, str) and any(pattern.search(value) for pattern in SENSITIVE_VALUE_PATTERNS):
        found.append(".".join(path) or "<value>")
    return tuple(found)


def ensure_secret_refs(value: Any) -> None:
    """Reject plaintext credentials before they can enter state or LLM history."""

    paths = plaintext_secret_paths(value)
    if paths:
        shown = ", ".join(paths[:4])
        raise SecretResolutionError(
            f"plaintext secret input detected at {shown}; replace each value with "
            "SecretRef('name') or {'$secret': 'name'} and configure a SecretResolver"
        )


def sanitize_secret_inputs(value: Any) -> Any:
    """Serialize references and redact invalid plaintext for diagnostic records."""

    serialized = serialize_secret_refs(value)
    paths = set(plaintext_secret_paths(serialized))

    def walk(item: Any, path: tuple[str, ...] = ()) -> Any:
        if is_secret_ref(item):
            return serialize_secret_refs(item)
        if ".".join(path) in paths or (not path and "<value>" in paths):
            return "[REDACTED:USE_SECRET_REF]"
        if isinstance(item, Mapping):
            return {str(key): walk(nested, (*path, str(key))) for key, nested in item.items()}
        if isinstance(item, (list, tuple)):
            return [walk(nested, (*path, str(index))) for index, nested in enumerate(item)]
        return item

    return walk(serialized)


def _contains_material(value: Any) -> bool:
    if is_secret_ref(value) or value is None:
        return False
    if isinstance(value, str):
        return bool(value) and not value.startswith(("[REDACTED", "[SECRET_REF:"))
    return isinstance(value, (bytes, bytearray, Mapping, list, tuple))


def _is_sensitive_key(normalized: str) -> bool:
    if normalized in NON_SECRET_TOKEN_KEYS:
        return False
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def resolve_secret_refs(
    value: Any,
    resolver: SecretResolver | None,
) -> tuple[Any, dict[str, Any]]:
    """Materialize a reference tree and return the values used for redaction."""

    resolved: dict[str, Any] = {}

    def walk(item: Any) -> Any:
        if is_secret_ref(item):
            reference = item if isinstance(item, SecretRef) else SecretRef(str(item[SECRET_REF_KEY]))
            if resolver is None:
                raise SecretResolutionError(
                    f"secret reference {reference.name!r} cannot be resolved; "
                    "configure Kernel(secret_resolver=...) or ToolRuntime(secret_resolver=...)"
                )
            try:
                material = resolver.resolve(reference)
            except SecretResolutionError:
                raise
            except Exception as exc:  # never include backend exception text; it may contain a value
                raise SecretResolutionError(
                    f"secret reference {reference.name!r} could not be resolved by the configured resolver"
                ) from exc
            resolved[reference.name] = material
            return material
        if isinstance(item, Mapping):
            return {key: walk(nested) for key, nested in item.items()}
        if isinstance(item, list):
            return [walk(nested) for nested in item]
        if isinstance(item, tuple):
            return tuple(walk(nested) for nested in item)
        return item

    return walk(value), resolved


def redact_secret_values(value: Any, resolved: Mapping[str, Any]) -> Any:
    """Replace resolved values reflected by a handler with safe references."""

    text_secrets = sorted(
        ((name, material) for name, material in resolved.items() if isinstance(material, str) and material),
        key=lambda item: len(item[1]),
        reverse=True,
    )
    byte_secrets = {
        material: name for name, material in resolved.items() if isinstance(material, bytes) and material
    }

    def walk(item: Any) -> Any:
        if isinstance(item, str):
            redacted = item
            for name, material in text_secrets:
                redacted = redacted.replace(material, f"[SECRET_REF:{name}]")
            return redacted
        if isinstance(item, bytes) and item in byte_secrets:
            return f"[SECRET_REF:{byte_secrets[item]}]"
        if isinstance(item, Mapping):
            return {str(key): walk(nested) for key, nested in item.items()}
        if isinstance(item, (list, tuple)):
            return [walk(nested) for nested in item]
        return item

    return walk(value)
