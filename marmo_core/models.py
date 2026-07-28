"""Data models for the Marmo-Core v1 unified resource surface."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable, Mapping
import re

from .security import ISOLATION_LEVELS


class ResourceKind(str, Enum):
    MEMORY = "memory"
    SKILL = "skill"
    TOOL = "tool"
    AGENT = "agent"


class LatencyClass(str, Enum):
    FAST = "fast"
    MEDIUM = "medium"
    SLOW = "slow"


class SideEffect(str, Enum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXTERNAL = "external"
    IRREVERSIBLE = "irreversible"


class TrustLevel(str, Enum):
    CORE = "core"
    VERIFIED = "verified"
    COMMUNITY = "community"
    UNTRUSTED = "untrusted"


KINDS = tuple(item.value for item in ResourceKind)
LATENCY_CLASSES = tuple(item.value for item in LatencyClass)
SIDE_EFFECTS = tuple(item.value for item in SideEffect)
TRUST_LEVELS = tuple(item.value for item in TrustLevel)

_SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)


@dataclass(frozen=True)
class ValidationIssue:
    """A validation issue reported for a resource file or definition."""

    message: str
    path: str = ""
    severity: str = "error"

    def to_dict(self) -> dict[str, str]:
        return {"severity": self.severity, "path": self.path, "message": self.message}


@dataclass(frozen=True)
class ResourceStats:
    """Operational metadata that can feed future scoring and auditing."""

    success_rate: float | None = None
    average_latency_ms: float | None = None
    average_cost: float | None = None
    last_used_at: str | None = None
    usage_count: int | None = None

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any] | None) -> "ResourceStats":
        if not data:
            return cls()
        return cls(
            success_rate=_optional_float(data.get("success_rate")),
            average_latency_ms=_optional_float(data.get("average_latency_ms")),
            average_cost=_optional_float(data.get("average_cost")),
            last_used_at=_optional_str(data.get("last_used_at")),
            usage_count=_optional_int(data.get("usage_count")),
        )

    def validate(self, path: str = "stats") -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        if self.success_rate is not None and not 0.0 <= self.success_rate <= 1.0:
            issues.append(ValidationIssue("success_rate must be between 0.0 and 1.0", f"{path}.success_rate"))
        for field_name in ("average_latency_ms", "average_cost"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                issues.append(ValidationIssue(f"{field_name} must be non-negative", f"{path}.{field_name}"))
        if self.usage_count is not None and self.usage_count < 0:
            issues.append(ValidationIssue("usage_count must be non-negative", f"{path}.usage_count"))
        return issues

    def to_dict(self) -> dict[str, Any]:
        return {
            "success_rate": self.success_rate,
            "average_latency_ms": self.average_latency_ms,
            "average_cost": self.average_cost,
            "last_used_at": self.last_used_at,
            "usage_count": self.usage_count,
        }


@dataclass(frozen=True)
class ResourceMetadata:
    """Common metadata shared by Memory, Skill, Tool, and Agent resources."""

    id: str
    kind: str
    name: str
    version: str
    description: str
    capabilities: tuple[str, ...]
    input_summary: str
    output_summary: str
    required_permissions: tuple[str, ...]
    cost_estimate: float
    latency_class: str
    side_effect: str
    trust_level: str
    ref: str
    tags: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    conflicts_with: tuple[str, ...] = ()
    stats: ResourceStats = field(default_factory=ResourceStats)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "ResourceMetadata":
        return cls(
            id=_required_str(data, "id"),
            kind=_required_str(data, "kind"),
            name=_required_str(data, "name"),
            version=_required_str(data, "version"),
            description=_required_str(data, "description"),
            capabilities=_str_tuple(data.get("capabilities"), "capabilities"),
            input_summary=_required_str(data, "input_summary"),
            output_summary=_required_str(data, "output_summary"),
            required_permissions=_str_tuple(data.get("required_permissions"), "required_permissions"),
            cost_estimate=_required_float(data, "cost_estimate"),
            latency_class=_required_str(data, "latency_class"),
            side_effect=_required_str(data, "side_effect"),
            trust_level=_required_str(data, "trust_level"),
            ref=_required_str(data, "ref"),
            tags=_str_tuple(data.get("tags"), "tags"),
            dependencies=_str_tuple(data.get("dependencies"), "dependencies"),
            conflicts_with=_str_tuple(data.get("conflicts_with"), "conflicts_with"),
            stats=ResourceStats.from_mapping(data.get("stats") if isinstance(data.get("stats"), Mapping) else None),
        )

    @property
    def identity(self) -> str:
        return f"{self.id}@{self.version}"

    def validate(self, path: str = "metadata") -> list[ValidationIssue]:
        issues: list[ValidationIssue] = []
        for field_name in (
            "id",
            "kind",
            "name",
            "version",
            "description",
            "input_summary",
            "output_summary",
            "latency_class",
            "side_effect",
            "trust_level",
            "ref",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                issues.append(ValidationIssue(f"{field_name} must be a non-empty string", f"{path}.{field_name}"))
        if self.kind not in KINDS:
            issues.append(ValidationIssue(f"kind must be one of: {', '.join(KINDS)}", f"{path}.kind"))
        if self.latency_class not in LATENCY_CLASSES:
            issues.append(ValidationIssue(f"latency_class must be one of: {', '.join(LATENCY_CLASSES)}", f"{path}.latency_class"))
        if self.side_effect not in SIDE_EFFECTS:
            issues.append(ValidationIssue(f"side_effect must be one of: {', '.join(SIDE_EFFECTS)}", f"{path}.side_effect"))
        if self.trust_level not in TRUST_LEVELS:
            issues.append(ValidationIssue(f"trust_level must be one of: {', '.join(TRUST_LEVELS)}", f"{path}.trust_level"))
        if not _SEMVER_RE.match(self.version):
            issues.append(ValidationIssue("version must be SemVer, for example 1.0.0", f"{path}.version"))
        if self.cost_estimate < 0:
            issues.append(ValidationIssue("cost_estimate must be non-negative", f"{path}.cost_estimate"))
        issues.extend(_validate_str_sequence(self.capabilities, f"{path}.capabilities"))
        issues.extend(_validate_str_sequence(self.required_permissions, f"{path}.required_permissions"))
        issues.extend(_validate_str_sequence(self.tags, f"{path}.tags"))
        issues.extend(_validate_str_sequence(self.dependencies, f"{path}.dependencies"))
        issues.extend(_validate_str_sequence(self.conflicts_with, f"{path}.conflicts_with"))
        issues.extend(self.stats.validate(f"{path}.stats"))
        return issues

    def search_text(self) -> str:
        """Return the lightweight metadata surface used for v1 retrieval."""

        parts: Iterable[str] = (
            self.id,
            self.kind,
            self.name,
            self.version,
            self.description,
            self.input_summary,
            self.output_summary,
            self.latency_class,
            self.side_effect,
            self.trust_level,
            self.ref,
            " ".join(self.capabilities),
            " ".join(self.required_permissions),
            " ".join(self.tags),
        )
        return " ".join(part for part in parts if part)

    def summary(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "kind": self.kind,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "required_permissions": list(self.required_permissions),
            "cost_estimate": self.cost_estimate,
            "latency_class": self.latency_class,
            "side_effect": self.side_effect,
            "trust_level": self.trust_level,
            "tags": list(self.tags),
        }
        # Omitted when empty to keep the routed-context token cost unchanged
        # for catalogs that do not annotate set-selection constraints.
        if self.dependencies:
            data["dependencies"] = list(self.dependencies)
        if self.conflicts_with:
            data["conflicts_with"] = list(self.conflicts_with)
        return data

    def to_dict(self) -> dict[str, Any]:
        data = self.summary()
        data.update(
            {
                "input_summary": self.input_summary,
                "output_summary": self.output_summary,
                "ref": self.ref,
                "stats": self.stats.to_dict(),
            }
        )
        return data


@dataclass(frozen=True)
class ResourceDefinition:
    """A resource definition loaded from a local package/file."""

    metadata: ResourceMetadata
    extras: dict[str, Any] = field(default_factory=dict)
    source: str = ""

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any], source: str = "") -> "ResourceDefinition":
        if "metadata" in data and isinstance(data["metadata"], Mapping):
            metadata_data = dict(data["metadata"])
            extras = {key: value for key, value in data.items() if key != "metadata"}
        else:
            metadata_keys = set(ResourceMetadata.__dataclass_fields__) - {"stats"}
            metadata_keys.add("stats")
            metadata_data = {key: value for key, value in data.items() if key in metadata_keys}
            extras = {key: value for key, value in data.items() if key not in metadata_keys}
        return cls(metadata=ResourceMetadata.from_mapping(metadata_data), extras=dict(extras), source=source)

    @property
    def identity(self) -> str:
        return self.metadata.identity

    def validate(self, path: str = "") -> list[ValidationIssue]:
        base = path or self.source or self.identity
        issues = self.metadata.validate(base)
        issues.extend(_validate_kind_extras(self.metadata.kind, self.extras, base))
        return issues

    def to_dict(self, include_extras: bool = True) -> dict[str, Any]:
        data = self.metadata.to_dict()
        if include_extras:
            data["extras"] = self.extras
        if self.source:
            data["source"] = self.source
        return data


@dataclass(frozen=True)
class SearchQuery:
    """Search inputs and filters for v1 retrieval."""

    task: str = ""
    keywords: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    kinds: tuple[str, ...] = ()
    trust_levels: tuple[str, ...] = ()
    side_effects: tuple[str, ...] = ()
    granted_permissions: tuple[str, ...] = ()
    require_permissions: bool = False
    top_k: int = 10
    per_kind_limits: Mapping[str, int] = field(default_factory=dict)
    min_score: float = 0.0


@dataclass(frozen=True)
class SearchResult:
    """A scored search result with explanation data."""

    resource: ResourceDefinition
    score: float
    reasons: tuple[str, ...]
    components: Mapping[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": round(self.score, 6),
            "reasons": list(self.reasons),
            "components": {key: round(value, 6) for key, value in self.components.items()},
            "resource": self.resource.metadata.summary(),
            "source": self.resource.source,
        }


SELECTION_STATUSES = ("selected", "abstain", "escalate")


@dataclass(frozen=True)
class SelectionResult:
    """Outcome of set selection (§15.6): a selected set, abstain, or escalate.

    Selectors must not always pick something: ``abstain`` says no defensible
    set exists (empty candidates, unresolvable dependencies, budget), and
    ``escalate`` says a set exists but needs a human decision (e.g. it is
    only feasible with permissions that were not granted).
    """

    results: tuple[SearchResult, ...]
    reason: str
    status: str = "selected"

    @property
    def selected(self) -> bool:
        return self.status == "selected"

    @property
    def by_kind(self) -> dict[str, list[SearchResult]]:
        grouped: dict[str, list[SearchResult]] = {kind: [] for kind in KINDS}
        for result in self.results:
            grouped.setdefault(result.resource.metadata.kind, []).append(result)
        return grouped

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason": self.reason,
            "resources": [result.to_dict() for result in self.results],
        }


# Backward-compatible name from v1, when selection could only return a set.
SelectedResourceSet = SelectionResult


def parse_resource_ref(value: str) -> tuple[str, str | None]:
    """Parse CLI resource references in either id or id@version form."""

    if "@" not in value:
        return value, None
    resource_id, version = value.rsplit("@", 1)
    return resource_id, version or None


def semver_major(version: str) -> int | None:
    match = _SEMVER_RE.match(version)
    if not match:
        return None
    return int(match.group(1))


def _validate_kind_extras(kind: str, extras: Mapping[str, Any], path: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if kind == ResourceKind.TOOL.value:
        input_schema = extras.get("input_schema")
        if input_schema is not None and not isinstance(input_schema, Mapping):
            issues.append(ValidationIssue("tool input_schema must be an object when provided", f"{path}.input_schema"))
        output_schema = extras.get("output_schema")
        if output_schema is not None and not isinstance(output_schema, Mapping):
            issues.append(ValidationIssue("tool output_schema must be an object when provided", f"{path}.output_schema"))
        isolation = extras.get("isolation_level")
        if isolation is not None and isolation not in ISOLATION_LEVELS:
            issues.append(
                ValidationIssue(
                    f"tool isolation_level must be one of: {', '.join(ISOLATION_LEVELS)}",
                    f"{path}.isolation_level",
                )
            )
    if kind == ResourceKind.AGENT.value:
        interface = extras.get("delegation_interface")
        if interface is not None and interface not in ("tool_wrap", "structured_task"):
            issues.append(
                ValidationIssue(
                    "agent delegation_interface must be tool_wrap or structured_task when provided",
                    f"{path}.delegation_interface",
                )
            )
    return issues


def _validate_str_sequence(values: tuple[str, ...], path: str) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    for index, value in enumerate(values):
        if not isinstance(value, str) or not value.strip():
            issues.append(ValidationIssue("value must be a non-empty string", f"{path}[{index}]"))
    return issues


def _required_str(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{key} must be a string")
    return value.strip()


def _optional_str(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def _required_float(data: Mapping[str, Any], key: str) -> float:
    value = data.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{key} must be a number")
    return float(value)


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _str_tuple(value: Any, key: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"{key} must be a list of strings")
    if not all(isinstance(item, str) for item in value):
        raise ValueError(f"{key} must be a list of strings")
    return tuple(item.strip() for item in value if item.strip())
