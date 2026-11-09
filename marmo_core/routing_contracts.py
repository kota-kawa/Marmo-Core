"""Typed, evidence-carrying contracts used by goal-aware routing.

The contract format is intentionally small.  It can say that a resource has
an observed affordance, that the affordance applies to a scope, and which
other resources must be available with it.  Missing or incomplete declarations
remain unknown; they are never treated as proof that an operation is
available.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence, TypeAlias

from .models import ResourceDefinition

SUPPORTED_MODES = frozenset({"effect", "information", "context"})


class TruthValue(str, Enum):
    """Three-valued result for matching a requirement against a contract."""

    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Provenance:
    """Source and evidence supporting a task or resource declaration."""

    source: str
    evidence: str = ""
    observed_at: str | None = None

    @classmethod
    def from_mapping(cls, value: Any) -> Provenance | None:
        if isinstance(value, str) and value.strip():
            return cls(source=value.strip())
        if not isinstance(value, Mapping):
            return None
        source = value.get("source")
        evidence = value.get("evidence", value.get("quote", ""))
        observed_at = value.get("observed_at")
        if not isinstance(source, str) or not source.strip():
            return None
        return cls(
            source=source.strip(),
            evidence=evidence.strip() if isinstance(evidence, str) else "",
            observed_at=observed_at.strip() if isinstance(observed_at, str) else None,
        )

    def to_mapping(self) -> dict[str, str]:
        value = {"source": self.source}
        if self.evidence:
            value["evidence"] = self.evidence
        if self.observed_at is not None:
            value["observed_at"] = self.observed_at
        return value


class RequirementExpression:
    """Base class for the AND/OR expression accepted by :class:`TaskSpec`."""


@dataclass(frozen=True)
class Requirement(RequirementExpression):
    """One typed capability requested by a task.

    ``None`` is allowed for fields extracted as unknown.  A requirement with
    an unknown action, entity type, or mode cannot be proven true.
    """

    action: str | None
    entity_type: str | None
    target_scope: str | None = None
    output_type: str | None = None
    mode: str | None = "effect"
    provenance: tuple[Provenance, ...] = ()
    unknown_items: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> Requirement:
        provenance = _parse_provenance(value.get("provenance"))
        provenance_unknown = _mapping_provenance_unknown(value, "provenance", provenance)
        unknown = list(_parse_unknown_items(value.get("unknown_items", ())))
        if _unknown_items_malformed(value.get("unknown_items", ())):
            unknown.append("requirement unknown_items is malformed")
        if provenance_unknown:
            unknown.append("requirement provenance is malformed")
        action, bad_action = _optional_mapping_text(value, "action")
        entity_type, bad_entity = _optional_mapping_text(value, "entity_type")
        target_scope, bad_scope = _optional_mapping_text(value, "target_scope", alias="scope")
        output_type, bad_output = _optional_mapping_text(value, "output_type")
        raw_mode = value.get("mode")
        mode = _optional_text(raw_mode)
        bad_mode = mode not in SUPPORTED_MODES
        for bad, label in (
            (bad_action or action is None, "action"),
            (bad_entity or entity_type is None, "entity_type"),
            (bad_scope, "target_scope"),
            (bad_output, "output_type"),
            (bad_mode, "mode"),
        ):
            if bad:
                unknown.append(f"requirement {label} is missing or malformed")
        return cls(
            action=action,
            entity_type=entity_type,
            target_scope=target_scope,
            output_type=output_type,
            mode=mode,
            provenance=provenance,
            unknown_items=tuple(dict.fromkeys(unknown)),
        )


@dataclass(frozen=True)
class AllOf(RequirementExpression):
    """Every child expression is required."""

    children: tuple["RequirementExpressionValue", ...]


@dataclass(frozen=True)
class OneOf(RequirementExpression):
    """At least one child expression is required."""

    children: tuple["RequirementExpressionValue", ...]


RequirementExpressionValue: TypeAlias = Requirement | AllOf | OneOf


@dataclass(frozen=True)
class TaskSpec:
    """Typed requirements and extraction gaps.

    Versioned vocabulary bindings are checked when both the task and resource
    contract declare them. If both omit a binding, action and entity terms are
    opaque strings compared by exact equality; this module does not claim that
    unversioned terms belong to a published ontology.
    """

    expression: RequirementExpressionValue | None
    prohibited_operations: tuple[str, ...] = ()
    unknown_items: tuple[str, ...] = ()
    provenance: tuple[Provenance, ...] = ()
    vocabulary_version: str | None = None
    vocabulary_hash: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> TaskSpec:
        """Parse a TaskSpec mapping.

        ``requirements`` accepts a requirement, a list (treated as AND), or
        nested ``{"all_of": [...]}`` / ``{"one_of": [...]}`` expressions.
        Malformed or omitted requirements are recorded as unknown.
        """

        unknown: list[str] = []
        raw_expression = value.get("requirements", value.get("expression"))
        expression = _parse_expression(raw_expression, unknown, "requirements")
        if raw_expression is None:
            unknown.append("requirements are missing")
        elif isinstance(expression, (AllOf, OneOf)) and not expression.children:
            unknown.append("requirements expression is empty")
        prohibited = _parse_text_sequence(
            value.get("prohibited_operations", ()), unknown, "prohibited_operations"
        )
        raw_unknown = value.get("unknown_items", ())
        if _unknown_items_malformed(raw_unknown):
            unknown.append("unknown_items is malformed")
        unknown.extend(_parse_unknown_items(raw_unknown))
        provenance = _parse_provenance(value.get("provenance"))
        if _mapping_provenance_unknown(value, "provenance", provenance):
            unknown.append("TaskSpec provenance is malformed")
        vocabulary_version = _optional_text(value.get("vocabulary_version"))
        vocabulary_hash = _optional_text(value.get("vocabulary_hash"))
        if "vocabulary_version" in value and vocabulary_version is None:
            unknown.append("TaskSpec vocabulary_version is malformed")
        if "vocabulary_hash" in value and not _valid_vocabulary_hash(vocabulary_hash):
            unknown.append("TaskSpec vocabulary_hash is malformed")
        if (vocabulary_version is None) != (vocabulary_hash is None):
            unknown.append("TaskSpec vocabulary version and hash must be supplied together")
        return cls(
            expression=expression,
            prohibited_operations=prohibited,
            unknown_items=tuple(dict.fromkeys(unknown)),
            provenance=provenance,
            vocabulary_version=vocabulary_version,
            vocabulary_hash=vocabulary_hash,
        )

    def to_mapping(self) -> dict[str, Any]:
        """Serialize all typed fields without dropping unknown state."""

        return {
            "requirements": _expression_to_mapping(self.expression),
            "prohibited_operations": list(self.prohibited_operations),
            "unknown_items": list(self.unknown_items),
            "provenance": [item.to_mapping() for item in self.provenance],
            **({"vocabulary_version": self.vocabulary_version} if self.vocabulary_version is not None else {}),
            **({"vocabulary_hash": self.vocabulary_hash} if self.vocabulary_hash is not None else {}),
        }


@dataclass(frozen=True)
class Affordance:
    """A resource capability in the shared contract vocabulary."""

    action: str | None
    entity_type: str | None
    supported_scope: str | None
    output_type: str | None
    mode: str | None
    provenance: tuple[Provenance, ...] = ()
    unknown_items: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> Affordance:
        action, bad_action = _optional_mapping_text(value, "action")
        entity_type, bad_entity = _optional_mapping_text(value, "entity_type")
        scope, bad_scope = _optional_mapping_text(value, "supported_scope", alias="scope")
        output_type, bad_output = _optional_mapping_text(value, "output_type")
        mode = _optional_text(value.get("mode"))
        provenance = _parse_provenance(value.get("provenance"))
        unknown: list[str] = []
        for bad, label in (
            (bad_action or action is None, "action"),
            (bad_entity or entity_type is None, "entity_type"),
            (bad_scope or scope is None, "supported_scope"),
            (bad_output, "output_type"),
            (mode not in SUPPORTED_MODES, "mode"),
            (_mapping_provenance_unknown(value, "provenance", provenance), "provenance"),
        ):
            if bad:
                unknown.append(f"affordance {label} is missing or malformed")
        return cls(
            action=action,
            entity_type=entity_type,
            supported_scope=scope,
            output_type=output_type,
            mode=mode,
            provenance=provenance,
            unknown_items=tuple(unknown),
        )


@dataclass(frozen=True)
class ResourceContract:
    """Observed routing declarations stored in ``ResourceDefinition.extras``."""

    observed: bool = False
    complete: bool = False
    affordances: tuple[Affordance, ...] = ()
    context_all_of: tuple[str, ...] = ()
    context_one_of: tuple[tuple[str, ...], ...] = ()
    call_preconditions: tuple[RequirementExpressionValue, ...] = ()
    permissions: tuple[str, ...] = ()
    source_evidence: tuple[Provenance, ...] = ()
    unknown_items: tuple[str, ...] = ()
    vocabulary_version: str | None = None
    vocabulary_hash: str | None = None

    @classmethod
    def from_resource(cls, resource: ResourceDefinition) -> ResourceContract:
        raw = resource.extras.get("routing_contract")
        return cls.from_mapping(raw if isinstance(raw, Mapping) else None)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> ResourceContract:
        if value is None:
            return cls(unknown_items=("routing_contract is missing or malformed",))

        unknown: list[str] = []
        version = value.get("schema_version", 1)
        if type(version) is not int or version != 1:
            unknown.append(f"unsupported routing_contract schema_version: {version!r}")
        observed_value = value.get("observed", value.get("status") == "observed")
        if not isinstance(observed_value, bool):
            unknown.append("routing_contract observed flag is malformed")
            observed = False
        else:
            observed = observed_value
        complete_value = value.get("complete", False)
        if not isinstance(complete_value, bool):
            unknown.append("routing_contract complete flag is malformed")
            complete = False
        else:
            complete = complete_value

        raw_affordances = value.get("affordances", ())
        affordances: list[Affordance] = []
        if isinstance(raw_affordances, Sequence) and not isinstance(raw_affordances, (str, bytes)):
            for index, raw_affordance in enumerate(raw_affordances):
                if isinstance(raw_affordance, Mapping):
                    affordance = Affordance.from_mapping(raw_affordance)
                    affordances.append(affordance)
                    unknown.extend(
                        f"affordances[{index}]: {item}"
                        for item in affordance.unknown_items
                    )
                else:
                    unknown.append(f"affordances[{index}] is malformed")
        else:
            unknown.append("routing_contract affordances must be a list")

        raw_context = value.get("context", {})
        context_all_of: tuple[str, ...] = ()
        context_one_of: tuple[tuple[str, ...], ...] = ()
        if isinstance(raw_context, Mapping):
            context_all_of = _parse_text_sequence(
                raw_context.get("all_of", ()), unknown, "context.all_of"
            )
            parsed_groups: list[tuple[str, ...]] = []
            raw_groups = raw_context.get("one_of", ())
            if isinstance(raw_groups, Sequence) and not isinstance(raw_groups, (str, bytes)):
                for index, group in enumerate(raw_groups):
                    if isinstance(group, Sequence) and not isinstance(group, (str, bytes)):
                        parsed = tuple(item.strip() for item in group if isinstance(item, str) and item.strip())
                        if parsed and len(parsed) == len(group):
                            parsed_groups.append(parsed)
                        else:
                            unknown.append(f"context.one_of[{index}] is malformed")
                    elif isinstance(group, str) and group.strip():
                        parsed_groups.append((group.strip(),))
                    else:
                        unknown.append(f"context.one_of[{index}] is malformed")
            else:
                unknown.append("context.one_of must be a list")
            context_one_of = tuple(parsed_groups)
        else:
            unknown.append("routing_contract context must be a mapping")

        raw_preconditions = value.get("call_preconditions", ())
        call_preconditions: list[RequirementExpressionValue] = []
        if isinstance(raw_preconditions, Sequence) and not isinstance(raw_preconditions, (str, bytes)):
            for index, raw_precondition in enumerate(raw_preconditions):
                expression = _parse_expression(raw_precondition, unknown, f"call_preconditions[{index}]")
                if expression is not None:
                    call_preconditions.append(expression)
        else:
            unknown.append("call_preconditions must be a list")

        permissions = _parse_text_sequence(value.get("permissions", ()), unknown, "permissions")
        raw_evidence = value.get("source_evidence")
        evidence = _parse_provenance(raw_evidence)
        if "source_evidence" in value and (
            raw_evidence is None or _provenance_unknown(raw_evidence, evidence)
        ):
            unknown.append("routing_contract source_evidence is malformed")
        if not evidence:
            unknown.append("routing_contract has no source_evidence")
        raw_unknown = value.get("unknown_items", ())
        if _unknown_items_malformed(raw_unknown):
            unknown.append("routing_contract unknown_items is malformed")
        unknown.extend(_parse_unknown_items(raw_unknown))
        vocabulary_version = _optional_text(value.get("vocabulary_version"))
        vocabulary_hash = _optional_text(value.get("vocabulary_hash"))
        if "vocabulary_version" in value and vocabulary_version is None:
            unknown.append("routing_contract vocabulary_version is malformed")
        if "vocabulary_hash" in value and not _valid_vocabulary_hash(vocabulary_hash):
            unknown.append("routing_contract vocabulary_hash is malformed")
        if (vocabulary_version is None) != (vocabulary_hash is None):
            unknown.append("routing_contract vocabulary version and hash must be supplied together")
        return cls(
            observed=observed,
            complete=complete,
            affordances=tuple(affordances),
            context_all_of=context_all_of,
            context_one_of=context_one_of,
            call_preconditions=tuple(call_preconditions),
            permissions=permissions,
            source_evidence=evidence,
            unknown_items=tuple(dict.fromkeys(unknown)),
            vocabulary_version=vocabulary_version,
            vocabulary_hash=vocabulary_hash,
        )


def match_requirement(requirement: Requirement, contract: ResourceContract, resource_kind: str) -> TruthValue:
    """Match one requirement against one observed resource contract.

    A complete, sourced declaration can disprove a capability.  An incomplete
    declaration, missing evidence, or an unsupported value yields UNKNOWN.
    Skills and memories can provide context or information, but never prove an
    ``effect`` requirement.
    """

    if requirement.unknown_items:
        return TruthValue.UNKNOWN
    if requirement.mode not in SUPPORTED_MODES:
        return TruthValue.UNKNOWN
    if contract.unknown_items:
        return TruthValue.UNKNOWN
    if requirement.mode == "effect" and resource_kind in {"memory", "skill"}:
        return TruthValue.FALSE
    if not contract.observed or not contract.source_evidence:
        return TruthValue.UNKNOWN

    saw_unknown = bool(contract.unknown_items)
    for affordance in contract.affordances:
        value = _match_affordance(requirement, affordance, resource_kind)
        if value is TruthValue.TRUE:
            if affordance.provenance or contract.source_evidence:
                return TruthValue.TRUE
            saw_unknown = True
        elif value is TruthValue.UNKNOWN:
            saw_unknown = True
    if saw_unknown or not contract.complete:
        return TruthValue.UNKNOWN
    return TruthValue.FALSE


def evaluate_expression(
    expression: RequirementExpressionValue | None,
    match_one: Any,
) -> TruthValue:
    """Evaluate an expression using a caller-supplied atomic matcher."""

    if expression is None:
        return TruthValue.UNKNOWN
    if isinstance(expression, Requirement):
        return match_one(expression)
    if not isinstance(expression, (AllOf, OneOf)):
        return TruthValue.UNKNOWN
    if not expression.children:
        return TruthValue.UNKNOWN
    child_values = [evaluate_expression(child, match_one) for child in expression.children]
    if isinstance(expression, AllOf):
        if any(item is TruthValue.FALSE for item in child_values):
            return TruthValue.FALSE
        if any(item is TruthValue.UNKNOWN for item in child_values):
            return TruthValue.UNKNOWN
        return TruthValue.TRUE
    if isinstance(expression, OneOf):
        if any(item is TruthValue.TRUE for item in child_values):
            return TruthValue.TRUE
        if any(item is TruthValue.UNKNOWN for item in child_values):
            return TruthValue.UNKNOWN
        return TruthValue.FALSE
    return TruthValue.UNKNOWN


def _match_affordance(
    requirement: Requirement, affordance: Affordance, resource_kind: str
) -> TruthValue:
    if affordance.unknown_items or affordance.mode not in SUPPORTED_MODES:
        return TruthValue.UNKNOWN
    checks = [
        _exact_match(requirement.action, affordance.action),
        _exact_match(requirement.entity_type, affordance.entity_type),
        _exact_match(requirement.mode, affordance.mode),
    ]
    if requirement.output_type is not None:
        checks.append(_exact_match(requirement.output_type, affordance.output_type))
    if requirement.target_scope is not None:
        checks.append(_scope_match(requirement.target_scope, affordance.supported_scope))
    if requirement.mode == "effect" and resource_kind not in {"tool", "agent"}:
        checks.append(TruthValue.FALSE)
    if any(item is TruthValue.FALSE for item in checks):
        return TruthValue.FALSE
    if any(item is TruthValue.UNKNOWN for item in checks):
        return TruthValue.UNKNOWN
    return TruthValue.TRUE


def _exact_match(required: str | None, offered: str | None) -> TruthValue:
    if not required or not offered:
        return TruthValue.UNKNOWN
    return TruthValue.TRUE if required.strip() == offered.strip() else TruthValue.FALSE


def _scope_match(required: str, offered: str | None) -> TruthValue:
    if not offered or not required.strip():
        return TruthValue.UNKNOWN
    requested = required.strip().strip("/")
    supported = offered.strip().strip("/")
    if supported in {"*", "global"}:
        return TruthValue.TRUE
    if requested in {"*", "global"}:
        return TruthValue.TRUE if supported == requested else TruthValue.FALSE
    if requested == supported or requested.startswith(supported + "/"):
        return TruthValue.TRUE
    return TruthValue.FALSE


def _parse_expression(
    value: Any, unknown: list[str], path: str
) -> RequirementExpressionValue | None:
    if isinstance(value, Requirement):
        return value
    if isinstance(value, (AllOf, OneOf)):
        return value
    if isinstance(value, RequirementExpression):
        unknown.append(f"{path} is an unsupported expression node")
        return None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        children = tuple(
            child
            for index, item in enumerate(value)
            if (child := _parse_expression(item, unknown, f"{path}[{index}]")) is not None
        )
        if not children:
            unknown.append(f"{path} is empty")
        return AllOf(children)
    if not isinstance(value, Mapping):
        unknown.append(f"{path} is malformed")
        return None
    if "all_of" in value or value.get("op") == "all_of":
        raw_children = value.get("all_of", value.get("children", ()))
        children = _parse_expression_children(raw_children, unknown, path)
        if not children:
            unknown.append(f"{path} all_of is empty")
        return AllOf(children)
    if "one_of" in value or value.get("op") == "one_of":
        raw_children = value.get("one_of", value.get("children", ()))
        children = _parse_expression_children(raw_children, unknown, path)
        if not children:
            unknown.append(f"{path} one_of is empty")
        return OneOf(children)
    if "action" in value or "entity_type" in value or "mode" in value:
        return Requirement.from_mapping(value)
    unknown.append(f"{path} does not describe a requirement")
    return None


def _parse_expression_children(
    value: Any, unknown: list[str], path: str
) -> tuple[RequirementExpressionValue, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        unknown.append(f"{path} expression children must be a list")
        return ()
    children: list[RequirementExpressionValue] = []
    for index, item in enumerate(value):
        parsed = _parse_expression(item, unknown, f"{path}[{index}]")
        if parsed is not None:
            children.append(parsed)
    return tuple(children)


def _expression_to_mapping(expression: RequirementExpressionValue | None) -> Any:
    if expression is None:
        return None
    if isinstance(expression, Requirement):
        value: dict[str, Any] = {
            "action": expression.action,
            "entity_type": expression.entity_type,
            "mode": expression.mode,
            "provenance": [item.to_mapping() for item in expression.provenance],
            "unknown_items": list(expression.unknown_items),
        }
        if expression.target_scope is not None:
            value["target_scope"] = expression.target_scope
        if expression.output_type is not None:
            value["output_type"] = expression.output_type
        return value
    if isinstance(expression, AllOf):
        return {"all_of": [_expression_to_mapping(child) for child in expression.children]}
    if isinstance(expression, OneOf):
        return {"one_of": [_expression_to_mapping(child) for child in expression.children]}
    return None


def _parse_provenance(value: Any) -> tuple[Provenance, ...]:
    if isinstance(value, Mapping) or isinstance(value, str):
        items = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, str)):
        items = list(value)
    else:
        return ()
    return tuple(item for raw in items if (item := Provenance.from_mapping(raw)) is not None)


def _mapping_provenance_unknown(
    value: Mapping[str, Any], key: str, parsed: tuple[Provenance, ...]
) -> bool:
    if key not in value:
        return False
    raw = value[key]
    return raw is None or _provenance_unknown(raw, parsed)


def _valid_vocabulary_hash(value: str | None) -> bool:
    return value is not None and len(value) == 64 and all(
        character in "0123456789abcdefABCDEF" for character in value
    )


def _provenance_unknown(value: Any, parsed: tuple[Provenance, ...]) -> bool:
    if value is None or value == () or value == []:
        return False
    if isinstance(value, (Mapping, str)):
        items = [value]
    elif isinstance(value, Sequence) and not isinstance(value, (bytes, str)):
        items = list(value)
    else:
        return True
    return len(parsed) != len(items)


def _parse_text_sequence(value: Any, unknown: list[str], path: str) -> tuple[str, ...]:
    if value is None:
        unknown.append(f"{path} must be a list of strings")
        return ()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        unknown.append(f"{path} must be a list of strings")
        return ()
    parsed: list[str] = []
    for index, item in enumerate(value):
        if isinstance(item, str) and item.strip():
            parsed.append(item.strip())
        else:
            unknown.append(f"{path}[{index}] is malformed")
    return tuple(dict.fromkeys(parsed))


def _parse_unknown_items(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _optional_mapping_text(
    value: Mapping[str, Any], key: str, *, alias: str | None = None
) -> tuple[str | None, bool]:
    selected_key = key if key in value else alias if alias is not None and alias in value else None
    if selected_key is None:
        return None, False
    raw = value[selected_key]
    if not isinstance(raw, str) or not raw.strip():
        return None, True
    return raw.strip(), False


def _unknown_items_malformed(value: Any) -> bool:
    if value == () or value == []:
        return False
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return True
    return any(not isinstance(item, str) or not item.strip() for item in value)


def _optional_text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None
