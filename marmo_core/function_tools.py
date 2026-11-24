"""Import function-calling tool definitions as Tool resources.

Agent stacks already describe their tools as JSON: OpenAI ``tools`` entries,
Anthropic ``tools`` entries, MCP ``tools/list`` items. ``function_tool_resources``
turns a list of them into ``tool`` resources, so a catalog of thousands of
functions can be indexed, searched, and narrowed to the few a goal needs
before they are sent to a model.

Accepted shapes (one list may mix them):

- OpenAI Chat Completions: ``{"type": "function", "function": {"name", "description", "parameters"}}``
- OpenAI Responses / legacy functions: ``{"name", "description", "parameters"}``
- Anthropic Messages: ``{"name", "description", "input_schema"}``
- MCP ``tools/list``: ``{"name", "description", "inputSchema", "outputSchema"?}``

Security defaults follow ``mcp_tool_resources``: the declarations come from
outside the library, so resources default to ``trust_level="community"`` and
``side_effect="external"`` and require the ``tools.<namespace>`` permission,
which a policy context must grant before any of them can activate. The
resources carry no implementation; executing one through the Kernel still
needs a ``tool_implementations`` entry for its id.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping, Sequence
import hashlib
import re

from .models import ResourceDefinition

_SUMMARY_LIMIT = 600


def function_tool_resources(
    specs: Iterable[Mapping[str, Any]],
    *,
    namespace: str,
    trust_level: str = "community",
    side_effect: str = "external",
    isolation_level: str = "L0",
    version: str = "0.1.0",
    required_permissions: Sequence[str] | None = None,
) -> list[ResourceDefinition]:
    """Tool resources for function-calling definitions, one per spec.

    Ids are ``tool.<namespace>.<function-name>`` (lower-cased, runs of other
    characters folded to ``-``; a name with no ASCII letters or digits, such
    as a Japanese one, becomes ``x`` plus a hash of it); two specs that fold
    to the same id raise ``ValueError`` rather than shadowing each other. ``required_permissions``
    replaces the default ``("tools.<namespace>",)``.
    """

    namespace_slug = _slug(namespace)
    permissions = list(required_permissions) if required_permissions is not None else [f"tools.{namespace_slug}"]
    definitions: list[ResourceDefinition] = []
    seen: dict[str, str] = {}
    for position, spec in enumerate(specs):
        name, description, input_schema, output_schema = _unwrap(spec, position)
        resource_id = f"tool.{namespace_slug}.{_slug(name)}"
        if resource_id in seen:
            raise ValueError(f"function names {seen[resource_id]!r} and {name!r} both map to {resource_id}")
        seen[resource_id] = name
        payload: dict[str, Any] = {
            "id": resource_id,
            "kind": "tool",
            "name": name,
            "version": version,
            "description": description or f"Function {name}.",
            "capabilities": [f"{namespace_slug}:{_slug(name)}"],
            "input_summary": schema_summary(input_schema) or "no arguments",
            "output_summary": schema_summary(output_schema) or "function result",
            "required_permissions": permissions,
            "cost_estimate": 0.0,
            "latency_class": "medium",
            "side_effect": side_effect,
            "trust_level": trust_level,
            "ref": f"function://{namespace_slug}/{name}",
            "tags": ["function", namespace_slug],
            "input_schema": dict(input_schema),
            "isolation_level": isolation_level,
        }
        if output_schema:
            payload["output_schema"] = dict(output_schema)
        definitions.append(ResourceDefinition.from_mapping(payload, source=f"function://{namespace_slug}"))
    return definitions


def _unwrap(spec: Mapping[str, Any], position: int) -> tuple[str, str, Mapping[str, Any], Mapping[str, Any]]:
    if not isinstance(spec, Mapping):
        raise ValueError(f"tool spec #{position} is not an object")
    function = spec.get("function")
    body: Mapping[str, Any] = function if isinstance(function, Mapping) else spec
    name = body.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"tool spec #{position} has no name")
    description = body.get("description") or ""
    if not isinstance(description, str):
        raise ValueError(f"tool spec {name!r} has a non-string description")
    input_schema: Mapping[str, Any] = next(
        (body[key] for key in ("parameters", "input_schema", "inputSchema") if isinstance(body.get(key), Mapping)),
        {},
    )
    output_schema: Mapping[str, Any] = next(
        (body[key] for key in ("output_schema", "outputSchema") if isinstance(body.get(key), Mapping)),
        {},
    )
    return name.strip(), description.strip(), input_schema, output_schema


def schema_summary(schema: Mapping[str, Any]) -> str:
    """Property names and their descriptions, for the searchable summary."""

    properties = schema.get("properties") if isinstance(schema, Mapping) else None
    if not isinstance(properties, Mapping) or not properties:
        return ""
    required = set(schema.get("required") or ())
    parts = []
    for key, value in properties.items():
        text = str(key) + (" (required)" if key in required else "")
        if isinstance(value, Mapping) and isinstance(value.get("description"), str) and value["description"].strip():
            text += ": " + value["description"].strip()
        parts.append(text)
    return "; ".join(parts)[:_SUMMARY_LIMIT]


def _slug(value: str) -> str:
    """ASCII slug; a name with no ASCII letters or digits gets a stable hash instead."""

    slug = re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")
    return slug or "x" + hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
