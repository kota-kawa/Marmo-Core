"""Output helpers for the v1 CLI."""

from __future__ import annotations

from typing import Sequence
import json
import sys
import textwrap

from .models import ResourceDefinition, SearchResult, SelectedResourceSet
from .policy import PolicyDecision


def print_json(data: object) -> None:
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    print()


def render_resource_table(resources: Sequence[ResourceDefinition]) -> str:
    rows = [
        [
            item.metadata.id,
            item.metadata.version,
            item.metadata.kind,
            item.metadata.trust_level,
            item.metadata.side_effect,
            ", ".join(item.metadata.tags[:4]),
            _short(item.metadata.description, 58),
        ]
        for item in resources
    ]
    return _table(["id", "version", "kind", "trust", "effect", "tags", "description"], rows)


def render_search_table(results: Sequence[SearchResult]) -> str:
    rows = [
        [
            f"{result.score:.3f}",
            result.resource.metadata.id,
            result.resource.metadata.version,
            result.resource.metadata.kind,
            result.resource.metadata.trust_level,
            result.resource.metadata.side_effect,
            _short("; ".join(result.reasons), 72),
        ]
        for result in results
    ]
    return _table(["score", "id", "version", "kind", "trust", "effect", "reason"], rows)


def render_selected_set(selected: SelectedResourceSet) -> str:
    lines = ["Selected set:"]
    if selected.status != "selected":
        lines.append(f"  status: {selected.status}")
    lines.append(f"  reason: {selected.reason}")
    if not selected.results:
        lines.append("  resources: none")
        return "\n".join(lines)
    for result in selected.results:
        metadata = result.resource.metadata
        lines.append(f"  - {metadata.kind}: {metadata.id}@{metadata.version} ({result.score:.3f})")
    return "\n".join(lines)


def render_inspection(resource: ResourceDefinition) -> str:
    metadata = resource.metadata
    lines = [
        f"{metadata.id}@{metadata.version}",
        f"kind: {metadata.kind}",
        f"name: {metadata.name}",
        f"description: {metadata.description}",
        f"capabilities: {', '.join(metadata.capabilities) or '-'}",
        f"input_summary: {metadata.input_summary}",
        f"output_summary: {metadata.output_summary}",
        f"required_permissions: {', '.join(metadata.required_permissions) or '-'}",
        f"cost_estimate: {metadata.cost_estimate}",
        f"latency_class: {metadata.latency_class}",
        f"side_effect: {metadata.side_effect}",
        f"trust_level: {metadata.trust_level}",
        f"ref: {metadata.ref}",
        f"tags: {', '.join(metadata.tags) or '-'}",
    ]
    stats = {key: value for key, value in metadata.stats.to_dict().items() if value is not None}
    if stats:
        lines.append("stats:")
        lines.extend(f"  {key}: {value}" for key, value in stats.items())
    if resource.extras:
        lines.append("extras:")
        for key, value in resource.extras.items():
            rendered = json.dumps(value, ensure_ascii=False, sort_keys=True)
            lines.append(f"  {key}: {_short(rendered, 120)}")
    if resource.source:
        lines.append(f"source: {resource.source}")
    return "\n".join(lines)


def render_policy_decision(decision: PolicyDecision) -> str:
    lines = [
        f"{decision.verdict}: {decision.resource_id}@{decision.resource_version}",
        f"  gate: {decision.gate}",
        f"  reason: {decision.reason}",
    ]
    if decision.missing_permissions:
        lines.append(f"  missing_permissions: {', '.join(decision.missing_permissions)}")
    if decision.isolation_level:
        lines.append(
            f"  isolation: {decision.isolation_level} (required {decision.required_isolation_level})"
        )
    if decision.dry_run:
        lines.append("  dry_run: true")
    return "\n".join(lines)


def _table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> str:
    if not rows:
        return "(no results)"
    widths = [len(header) for header in headers]
    normalized_rows = [[str(cell) for cell in row] for row in rows]
    for row in normalized_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], min(len(cell), 80))
    separator = "  "
    header_line = separator.join(header.ljust(widths[index]) for index, header in enumerate(headers))
    rule = separator.join("-" * widths[index] for index in range(len(headers)))
    body = [separator.join(_wrap_cell(cell, widths[index]) for index, cell in enumerate(row)) for row in normalized_rows]
    return "\n".join([header_line, rule, *body])


def _wrap_cell(value: str, width: int) -> str:
    short = _short(value, width)
    return short.ljust(width)


def _short(value: str, width: int) -> str:
    value = textwrap.shorten(value.replace("\n", " "), width=max(width, 8), placeholder="...")
    return value
