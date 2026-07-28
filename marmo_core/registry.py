"""In-memory resource registry for Marmo-Core v1."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .errors import ResourceNotFoundError, ResourceValidationError
from .models import KINDS, ResourceDefinition, parse_resource_ref


class ResourceRegistry:
    """Registry keyed by resource id and SemVer version."""

    def __init__(self) -> None:
        self._resources: dict[tuple[str, str], ResourceDefinition] = {}
        self._by_id: dict[str, list[ResourceDefinition]] = defaultdict(list)
        self._disabled: set[tuple[str, str]] = set()
        self._revision = 0

    @property
    def revision(self) -> int:
        """Monotonic change counter used to invalidate retrieval indexes."""

        return self._revision

    def add(self, definition: ResourceDefinition) -> None:
        issues = definition.validate()
        if issues:
            joined = "\n".join(f"{issue.path}: {issue.message}" for issue in issues)
            raise ResourceValidationError(joined)
        key = (definition.metadata.id, definition.metadata.version)
        if key in self._resources:
            raise ResourceValidationError(f"duplicate resource identity: {definition.identity}")
        self._resources[key] = definition
        self._by_id[definition.metadata.id].append(definition)
        self._by_id[definition.metadata.id].sort(key=lambda item: item.metadata.version, reverse=True)
        self._revision += 1

    def extend(self, definitions: Iterable[ResourceDefinition]) -> None:
        for definition in definitions:
            self.add(definition)

    def replace(self, definition: ResourceDefinition) -> None:
        """Swap an already-registered id@version for an updated definition.

        Used by the Execution Evaluator (F-LOG-08) to write measured stats
        back onto resources (F-REG-05). The revision counter is bumped so
        retrieval indexes rebuild — the composite score depends on stats.
        """

        issues = definition.validate()
        if issues:
            joined = "\n".join(f"{issue.path}: {issue.message}" for issue in issues)
            raise ResourceValidationError(joined)
        key = (definition.metadata.id, definition.metadata.version)
        if key not in self._resources:
            raise ResourceNotFoundError(f"resource not found: {definition.identity}")
        self._resources[key] = definition
        versions = self._by_id[definition.metadata.id]
        for index, existing in enumerate(versions):
            if existing.metadata.version == definition.metadata.version:
                versions[index] = definition
                break
        self._revision += 1

    def disable(self, resource_id: str, version: str | None = None) -> None:
        """Keep a resource registered while removing it from use (F-REG-03)."""

        definition = self._resolve(resource_id, version, include_disabled=True)
        key = (definition.metadata.id, definition.metadata.version)
        if key not in self._disabled:
            self._disabled.add(key)
            self._revision += 1

    def enable(self, resource_id: str, version: str | None = None) -> None:
        """Make a disabled resource available to retrieval and activation again."""

        definition = self._resolve(resource_id, version, include_disabled=True)
        key = (definition.metadata.id, definition.metadata.version)
        if key in self._disabled:
            self._disabled.remove(key)
            self._revision += 1

    def is_enabled(self, resource_id: str, version: str | None = None) -> bool:
        definition = self._resolve(resource_id, version, include_disabled=True)
        return (definition.metadata.id, definition.metadata.version) not in self._disabled

    def all(self, *, include_disabled: bool = False) -> list[ResourceDefinition]:
        return sorted(
            (
                definition
                for key, definition in self._resources.items()
                if include_disabled or key not in self._disabled
            ),
            key=lambda definition: (definition.metadata.kind, definition.metadata.id, definition.metadata.version),
        )

    def list(
        self,
        *,
        kinds: Iterable[str] = (),
        trust_levels: Iterable[str] = (),
        side_effects: Iterable[str] = (),
        tags: Iterable[str] = (),
    ) -> list[ResourceDefinition]:
        kinds_set = {item for item in kinds if item}
        trust_set = {item for item in trust_levels if item}
        side_set = {item for item in side_effects if item}
        tag_set = {item for item in tags if item}
        resources = []
        for definition in self.all():
            metadata = definition.metadata
            if kinds_set and metadata.kind not in kinds_set:
                continue
            if trust_set and metadata.trust_level not in trust_set:
                continue
            if side_set and metadata.side_effect not in side_set:
                continue
            if tag_set and not tag_set.issubset(set(metadata.tags)):
                continue
            resources.append(definition)
        return resources

    def get(
        self,
        resource_id: str,
        version: str | None = None,
        *,
        include_disabled: bool = False,
    ) -> ResourceDefinition:
        return self._resolve(resource_id, version, include_disabled=include_disabled)

    def _resolve(
        self,
        resource_id: str,
        version: str | None,
        *,
        include_disabled: bool,
    ) -> ResourceDefinition:
        if version is None and "@" in resource_id:
            resource_id, version = parse_resource_ref(resource_id)
        if version is not None:
            key = (resource_id, version)
            if key not in self._resources:
                raise ResourceNotFoundError(f"resource not found: {resource_id}@{version}")
            if not include_disabled and key in self._disabled:
                raise ResourceNotFoundError(
                    f"resource is disabled: {resource_id}@{version}; enable it before use"
                )
            return self._resources[key]
        matches = [
            definition
            for definition in self._by_id.get(resource_id, [])
            if include_disabled
            or (definition.metadata.id, definition.metadata.version) not in self._disabled
        ]
        if not matches:
            disabled = self._by_id.get(resource_id, [])
            if disabled and not include_disabled:
                versions = ", ".join(definition.metadata.version for definition in disabled)
                raise ResourceNotFoundError(
                    f"resource is disabled: {resource_id} ({versions}); enable it before use"
                )
            raise ResourceNotFoundError(f"resource not found: {resource_id}")
        if len(matches) > 1:
            versions = ", ".join(definition.metadata.version for definition in matches)
            raise ResourceNotFoundError(f"resource id is ambiguous, specify version: {resource_id} ({versions})")
        return matches[0]

    def summary(self) -> dict[str, int]:
        counts = {kind: 0 for kind in KINDS}
        for definition in self.all():
            counts[definition.metadata.kind] = counts.get(definition.metadata.kind, 0) + 1
        counts["total"] = sum(counts[kind] for kind in KINDS)
        if self._disabled:
            counts["disabled"] = len(self._disabled)
        return counts

    def __len__(self) -> int:
        return len(self._resources)
