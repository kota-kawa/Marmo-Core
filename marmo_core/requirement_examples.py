"""Teach a TaskSpec extractor a catalog's conventions from earlier executions.

A requirement matches a resource contract only when its five typed fields
agree with a declared affordance, and which values a catalog uses is its
author's convention.  ``RequirementExample`` records an earlier task as its
goal text and the ids of the resources whose calls succeeded.  For a new
task, ``example_conventions`` looks those ids up in the *current* resources
and writes the affordances they declare as worked examples for
``GroundedTaskSpecExtractor(conventions=...)``.  Nobody has to author a
TaskSpec, and a catalog author who rewrites a contract does not have to
rewrite the examples.

An example teaches how a requirement is written; it grants no permission or
capability.  A resource that is no longer present, or whose contract is not
observed, contributes nothing.

This module is research code (opt-in).  The Kernel does not use it by default.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Iterable, Mapping, Sequence

from .llm import LLMProvider
from .models import ResourceDefinition
from .requirement_grounding import AffordanceOption, GroundedTaskSpecExtractor, affordance_menu
from .routing_contracts import TaskSpec

_SUCCESS = "success"


@dataclass(frozen=True)
class RequirementExample:
    """An earlier task: its goal and the resources whose calls succeeded, in first-use order."""

    goal: str
    resource_ids: tuple[str, ...]


def example_from_results(goal: str, results: Iterable[Any]) -> RequirementExample | None:
    """Build an example from the tool and agent results of one run.

    ``results`` are ``ToolResult`` / ``AgentResult`` objects or their mapping
    form, in call order.  Only calls with status ``success`` count; a dry run
    changed nothing and is ignored.  Returns ``None`` when no call succeeded.
    """

    ids: list[str] = []
    for result in results:
        get = result.get if isinstance(result, Mapping) else lambda key, _result=result: getattr(_result, key, None)
        identity = get("tool_id") or get("agent_id")
        if get("status") == _SUCCESS and isinstance(identity, str) and identity and identity not in ids:
            ids.append(identity)
    return RequirementExample(goal, tuple(ids)) if ids and isinstance(goal, str) and goal.strip() else None


def resolve_examples(
    examples: Iterable[RequirementExample], resources: Iterable[ResourceDefinition]
) -> list[tuple[str, tuple[AffordanceOption, ...]]]:
    """Pair each example's goal with the affordances its resources declare now.

    Affordances keep the order of the example's resources, without repeats.
    An example none of whose resources resolves is dropped.
    """

    declared: dict[str, tuple[AffordanceOption, ...]] = {}
    for resource in resources:
        declared[resource.metadata.id] = affordance_menu([resource]).options
    resolved = []
    for example in examples:
        options = tuple(dict.fromkeys(
            option for identity in example.resource_ids for option in declared.get(identity, ())
        ))
        if options:
            resolved.append((example.goal, options))
    return resolved


def render_conventions(
    examples: Sequence[tuple[str, Sequence[AffordanceOption]]], *, worked_examples: bool = True
) -> str:
    """The conventions text: the capability descriptions seen, then each goal with its capabilities.

    With ``worked_examples=False`` only the list of descriptions is written.
    Returns an empty string when there is nothing to show.
    """

    def line(option: AffordanceOption) -> str:
        return (f"action={option.action} entity_type={option.entity_type} target_scope={option.scope} "
                f"output_type={option.output_type} mode={option.mode}")

    seen = sorted({option for _, options in examples for option in options},
                  key=lambda item: (item.action, item.entity_type, item.scope, item.output_type, item.mode))
    if not seen:
        return ""
    parts = ["Conventions of this catalog, learned from earlier requests in the same domain.",
             "Capability descriptions seen so far:"]
    parts += [f"- {line(option)}" for option in seen]
    if worked_examples:
        parts.append("Earlier requests and the capabilities they needed:")
        for goal, options in examples:
            parts.append("Request: " + json.dumps(goal, ensure_ascii=False))
            parts.append("Capabilities: " + "; ".join(line(option) for option in options))
    return "\n".join(parts)


def example_conventions(
    examples: Iterable[RequirementExample],
    resources: Iterable[ResourceDefinition],
    *,
    worked_examples: bool = True,
) -> str:
    """Conventions text for ``examples`` against the affordances ``resources`` declare now."""

    return render_conventions(resolve_examples(examples, resources), worked_examples=worked_examples)


class ExampleGuidedTaskSpecProvider:
    """A ``TaskSpecProvider`` that extracts with conventions taught by earlier executions.

    Pass an instance to ``GoalAwareSetSelector``.  ``resources`` is read on
    every call, so the examples follow the contracts as they are now.  The
    remaining keyword arguments go to ``GroundedTaskSpecExtractor`` (a
    complete ``vocabulary`` is required, because no menu is shown).
    """

    def __init__(
        self,
        llm: LLMProvider,
        examples: Sequence[RequirementExample],
        resources: Iterable[ResourceDefinition],
        **extractor_options: Any,
    ) -> None:
        if "conventions" in extractor_options:
            raise ValueError("conventions are built from the examples")
        self.llm = llm
        self.examples = tuple(examples)
        self.resources = resources
        self.extractor_options = extractor_options

    def __call__(self, goal: str) -> TaskSpec:
        conventions = example_conventions(self.examples, self.resources)
        return GroundedTaskSpecExtractor(self.llm, conventions=conventions, **self.extractor_options).extract(goal)
