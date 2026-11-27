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

``FunctionToolkit`` covers the case where the tools are Python functions
rather than JSON: its ``tool`` decorator derives the same kind of definition
from a function's signature and docstring and keeps the function as the
handler. The security defaults are the same.
"""

from __future__ import annotations

from types import NoneType, UnionType
from typing import Annotated, Any, Callable, Iterable, Literal, Mapping, Sequence, TypeVar, Union, overload
from typing import get_args, get_origin, get_type_hints
import collections.abc
import hashlib
import inspect
import re

from .models import ResourceDefinition

_SUMMARY_LIMIT = 600

_Function = TypeVar("_Function", bound=Callable[..., Any])

_JSON_TYPES: dict[Any, str] = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    NoneType: "null",
    list: "array",
    tuple: "array",
    collections.abc.Sequence: "array",
    dict: "object",
    collections.abc.Mapping: "object",
}


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


class FunctionToolkit:
    """Register Python functions as Tool resources with a decorator.

    .. code-block:: python

        crm = FunctionToolkit("crm", side_effect="read")

        @crm.tool
        def find_customer(email: str, limit: int = 5) -> list[dict]:
            '''Look up customers by email address.'''
            ...

        registry.extend(crm.resources)
        Kernel(registry, llm, tool_implementations=crm.implementations, ...)

    Each decorated function becomes one ``tool.<namespace>.<function-name>``
    resource built by ``function_tool_resources``, so ids, summaries, and the
    defaults (``community``, ``external``, the ``tools.<namespace>``
    permission) are the same as for imported JSON definitions. The decorator
    returns the function unchanged.

    The input schema comes from the signature: ``str``, ``int``, ``float``,
    ``bool``, ``list`` / ``tuple`` / ``Sequence``, ``dict`` / ``Mapping``,
    ``None``, unions of those, and ``Literal`` values map to the schema types
    argument validation checks; ``Annotated[T, "text"]`` adds a description;
    a parameter without an annotation, or annotated ``Any``, accepts any
    value. Parameters without a default are required and unknown arguments
    are rejected. Any other annotation, ``*args`` / ``**kwargs``, and
    positional-only parameters raise ``ValueError``: arguments arrive as
    JSON and are passed by keyword.
    """

    def __init__(
        self,
        namespace: str,
        *,
        trust_level: str = "community",
        side_effect: str = "external",
        isolation_level: str = "L0",
        version: str = "0.1.0",
        required_permissions: Sequence[str] | None = None,
    ) -> None:
        self.namespace = namespace
        self.trust_level = trust_level
        self.side_effect = side_effect
        self.isolation_level = isolation_level
        self.version = version
        self.required_permissions = tuple(required_permissions) if required_permissions is not None else None
        self._definitions: dict[str, ResourceDefinition] = {}
        self._handlers: dict[str, Callable[..., Any]] = {}

    @overload
    def tool(self, function: _Function) -> _Function: ...

    @overload
    def tool(
        self,
        *,
        name: str | None = None,
        description: str | None = None,
        side_effect: str | None = None,
        required_permissions: Sequence[str] | None = None,
    ) -> Callable[[_Function], _Function]: ...

    def tool(
        self,
        function: _Function | None = None,
        *,
        name: str | None = None,
        description: str | None = None,
        side_effect: str | None = None,
        required_permissions: Sequence[str] | None = None,
    ) -> _Function | Callable[[_Function], _Function]:
        """Register a function; usable bare (``@kit.tool``) or with options.

        ``name`` and ``description`` default to the function's name and the
        first paragraph of its docstring. ``side_effect`` and
        ``required_permissions`` override the toolkit's values for this one
        function. A function with neither a docstring nor ``description`` is
        refused, since retrieval has nothing to match it by.
        """

        def register(target: _Function) -> _Function:
            tool_name = name if name is not None else str(getattr(target, "__name__", ""))
            text = description if description is not None else _first_paragraph(inspect.getdoc(target) or "")
            if not text.strip():
                raise ValueError(f"function {tool_name!r} needs a docstring or description= to be found by retrieval")
            permissions = required_permissions if required_permissions is not None else self.required_permissions
            (definition,) = function_tool_resources(
                [{"name": tool_name, "description": text, "input_schema": _signature_schema(target, tool_name)}],
                namespace=self.namespace,
                trust_level=self.trust_level,
                side_effect=side_effect or self.side_effect,
                isolation_level=self.isolation_level,
                version=self.version,
                required_permissions=permissions,
            )
            if definition.identity in self._definitions:
                raise ValueError(f"{definition.identity} is already registered in this toolkit")
            self._definitions[definition.identity] = definition
            self._handlers[definition.identity] = target
            return target

        return register(function) if function is not None else register

    @property
    def resources(self) -> list[ResourceDefinition]:
        """The registered Tool resources, in registration order."""

        return list(self._definitions.values())

    @property
    def implementations(self) -> dict[str, Callable[..., Any]]:
        """Handlers keyed by ``id@version``, for ``tool_implementations=``."""

        return dict(self._handlers)


def _first_paragraph(text: str) -> str:
    return " ".join(text.strip().split("\n\n", 1)[0].split())


def _signature_schema(function: Callable[..., Any], name: str) -> dict[str, Any]:
    """Input schema for a function called with keyword arguments."""

    hints = get_type_hints(function, include_extras=True)
    properties: dict[str, Any] = {}
    required: list[str] = []
    for parameter in inspect.signature(function).parameters.values():
        if parameter.kind not in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY):
            raise ValueError(
                f"function {name!r}: parameter {parameter.name!r} cannot be passed by keyword; "
                "tools take named arguments only"
            )
        try:
            properties[parameter.name] = _annotation_schema(hints.get(parameter.name, Any))
        except ValueError as error:
            raise ValueError(f"function {name!r}: parameter {parameter.name!r} {error}") from None
        if parameter.default is inspect.Parameter.empty:
            required.append(parameter.name)
    schema: dict[str, Any] = {"type": "object", "properties": properties, "additionalProperties": False}
    if required:
        schema["required"] = required
    return schema


def _annotation_schema(annotation: Any) -> dict[str, Any]:
    if get_origin(annotation) is Annotated:
        inner, *extras = get_args(annotation)
        schema = _annotation_schema(inner)
        text = next((extra for extra in extras if isinstance(extra, str) and extra.strip()), None)
        if text is not None:
            schema["description"] = text.strip()
        return schema
    if get_origin(annotation) is Literal:
        values = list(get_args(annotation))
        return {"type": _type_names([type(value) for value in values]), "enum": values}
    if annotation is Any:
        return {}
    members = get_args(annotation) if get_origin(annotation) in (Union, UnionType) else (annotation,)
    return {"type": _type_names(members)}


def _type_names(annotations: Sequence[Any]) -> str | list[str]:
    names: list[str] = []
    for annotation in annotations:
        name = _JSON_TYPES.get(get_origin(annotation) or annotation)
        if name is None:
            raise ValueError(
                f"has an annotation with no JSON schema type: {annotation!r}; use str, int, float, bool, "
                "list, dict, None, a union or Literal of those, or Any"
            )
        if name not in names:
            names.append(name)
    return names[0] if len(names) == 1 else names


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
