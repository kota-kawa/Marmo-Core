"""Exception types used by Marmo-Core v1."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MarmoError(Exception):
    """Base exception carrying a human-readable message."""

    message: str

    def __str__(self) -> str:
        return self.message


class ResourceValidationError(MarmoError):
    """Raised when a resource definition cannot be validated."""


class ResourceLoadError(MarmoError):
    """Raised when a resource file cannot be read or decoded."""


class PackageError(MarmoError):
    """Base error for local resource package operations."""


class PackageCompatibilityError(PackageError):
    """Raised when a package cannot run on the current kernel version."""


class PackageIntegrityError(PackageError):
    """Raised when a package lock or content hash cannot be verified."""


class ResourceNotFoundError(MarmoError):
    """Raised when a requested resource is absent or ambiguous."""


class ActivationError(MarmoError):
    """Raised when a resource entity cannot be resolved or activated."""


class ToolInputError(MarmoError):
    """Raised when tool arguments do not satisfy the tool input schema."""


class SecretResolutionError(ToolInputError):
    """Raised when a SecretRef cannot be materialized safely."""


class ProviderError(MarmoError):
    """Raised when a remote LLM or embedding provider cannot be reached or rejects a request."""


@dataclass(frozen=True)
class ProviderHTTPError(ProviderError):
    """An HTTP error from a provider, carrying the status and the response body.

    The body is preserved so a rejected request explains itself (for example
    an unsupported parameter or an invalid tool name) instead of surfacing as
    a bare ``HTTP Error 400``.
    """

    status: int = 0
    body: str = ""
    url: str = ""
