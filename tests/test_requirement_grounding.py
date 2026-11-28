from __future__ import annotations

from typing import Any, Sequence
import unittest

from marmo_core.llm import ChatMessage, LLMProvider, LLMResponse, LLMToolSpec, ToolCall
from marmo_core.models import ResourceDefinition, SearchResult
from marmo_core.registry import ResourceRegistry
from marmo_core.requirement_grounding import (
    AffordanceOption,
    GroundedTaskSpecExtractor,
    GroundedTaskSpecProvider,
    affordance_menu,
    supported_quote,
)
from marmo_core.retriever import Retriever
from marmo_core.routing_contracts import AllOf, Requirement
from marmo_core.selector import SelectionContext
from marmo_core.sufficient_selector import GoalAwareSetSelector

_HASH = "a" * 64
_GOAL = "Sort work/names.txt into out/names.txt and commit the result."
_VOCABULARY = {
    "action": ("read", "sort", "commit", "delete"),
    "entity_type": ("file", "repository", "commit"),
    "output_type": ("record", "state"),
    "mode": ("effect", "information"),
}


def _definition(
    resource_id: str,
    affordances: Sequence[tuple[str, str, str, str]],
    *,
    permissions: tuple[str, ...] = (),
    binding: tuple[str, str] | None = ("v1", _HASH),
    **contract_overrides: object,
) -> ResourceDefinition:
    contract: dict[str, object] = {
        "schema_version": 1,
        "observed": True,
        "complete": True,
        "affordances": [
            {
                "action": action,
                "entity_type": entity,
                "supported_scope": "workspace",
                "output_type": output,
                "mode": mode,
            }
            for action, entity, output, mode in affordances
        ],
        "context": {"all_of": [], "one_of": []},
        "call_preconditions": [],
        "permissions": list(permissions),
        "source_evidence": [{"source": "catalog", "evidence": "checked declaration"}],
    }
    if binding is not None:
        contract.update(vocabulary_version=binding[0], vocabulary_hash=binding[1])
    contract.update(contract_overrides)
    return ResourceDefinition.from_mapping(
        {
            "id": resource_id,
            "kind": "tool",
            "name": resource_id,
            "version": "1.0.0",
            "description": f"Resource {resource_id}",
            "capabilities": [],
            "input_summary": "input",
            "output_summary": "output",
            "required_permissions": list(permissions),
            "cost_estimate": 0.0,
            "latency_class": "fast",
            "side_effect": "none",
            "trust_level": "verified",
            "ref": f"tool://{resource_id}",
            "tags": [],
            "routing_contract": contract,
        }
    )


def _catalog() -> list[ResourceDefinition]:
    return [
        _definition("tool.test.sort", [("sort", "repository", "state", "effect")], permissions=("repo.write",)),
        _definition("tool.test.commit", [("commit", "commit", "state", "effect")], permissions=("repo.commit",)),
        _definition("tool.test.read", [("read", "repository", "record", "information")]),
    ]


class _Scripted(LLMProvider):
    def __init__(self, arguments: Any = None, *, content: str = "", error: Exception | None = None) -> None:
        self.arguments, self.content, self.error = arguments, content, error
        self.requests: list[tuple[Sequence[ChatMessage], Sequence[LLMToolSpec]]] = []

    def complete(self, messages: Sequence[ChatMessage], tools: Sequence[LLMToolSpec] = ()) -> LLMResponse:
        self.requests.append((messages, tools))
        if self.error is not None:
            raise self.error
        if self.arguments is None:
            return LLMResponse(self.content)
        return LLMResponse("", (ToolCall("call-1", "emit_requirements", self.arguments),))


def _answer(*requirements: dict[str, Any], unmet: Sequence[str] = (), ambiguities: Sequence[str] = ()) -> dict[str, Any]:
    return {"requirements": list(requirements), "unmet": list(unmet), "ambiguities": list(ambiguities)}


def _leaves(spec) -> list[Requirement]:
    assert isinstance(spec.expression, AllOf)
    return [child for child in spec.expression.children if isinstance(child, Requirement)]


class AffordanceMenuTest(unittest.TestCase):
    def test_menu_is_sorted_deduplicated_and_carries_no_resource_identity(self) -> None:
        catalog = [*_catalog(), _definition("tool.test.sort-again", [("sort", "repository", "state", "effect")])]
        menu = affordance_menu(reversed(catalog))
        self.assertEqual(
            menu.options,
            (
                AffordanceOption("commit", "commit", "workspace", "state", "effect"),
                AffordanceOption("read", "repository", "workspace", "record", "information"),
                AffordanceOption("sort", "repository", "workspace", "state", "effect"),
            ),
        )
        self.assertEqual((menu.vocabulary_version, menu.vocabulary_hash, menu.consistent), ("v1", _HASH, True))

    def test_unobserved_and_unknown_contracts_contribute_nothing(self) -> None:
        menu = affordance_menu(
            [
                _definition("tool.test.hidden", [("delete", "file", "state", "effect")], observed=False),
                _definition("tool.test.partial", [("delete", "file", "state", "effect")], schema_version=2),
                _definition("tool.test.read", [("read", "repository", "record", "information")]),
            ]
        )
        self.assertEqual([option.action for option in menu.options], ["read"])

    def test_capabilities_that_need_missing_permissions_stay_on_the_menu(self) -> None:
        menu = affordance_menu(_catalog())
        self.assertIn("commit", [option.action for option in menu.options])

    def test_mixed_vocabulary_bindings_are_reported_as_inconsistent(self) -> None:
        menu = affordance_menu(
            [
                _definition("tool.test.a", [("read", "file", "record", "information")]),
                _definition("tool.test.b", [("sort", "file", "state", "effect")], binding=("v2", "b" * 64)),
            ]
        )
        self.assertFalse(menu.consistent)


class SupportedQuoteTest(unittest.TestCase):
    def test_wrapping_quotation_marks_and_spaces_are_removed(self) -> None:
        self.assertEqual(supported_quote(' "commit the result" ', _GOAL), "commit the result")
        self.assertEqual(supported_quote("“Sort work/names.txt”", _GOAL), "Sort work/names.txt")

    def test_text_that_is_not_in_the_goal_is_rejected(self) -> None:
        self.assertIsNone(supported_quote("push the result", _GOAL))
        self.assertIsNone(supported_quote('""', _GOAL))
        self.assertIsNone(supported_quote(None, _GOAL))


class GroundedExtractionTest(unittest.TestCase):
    def test_requirements_use_the_menu_entry_fields_exactly(self) -> None:
        llm = _Scripted(
            _answer(
                {"option": 3, "evidence": "Sort work/names.txt"},
                {"option": 1, "evidence": '"commit the result"'},
            )
        )
        spec = GroundedTaskSpecExtractor(llm).extract(_GOAL, _catalog())

        self.assertEqual(spec.unknown_items, ())
        self.assertEqual(
            [(r.action, r.entity_type, r.target_scope, r.output_type, r.mode) for r in _leaves(spec)],
            [("sort", "repository", "workspace", "state", "effect"), ("commit", "commit", "workspace", "state", "effect")],
        )
        self.assertEqual(_leaves(spec)[1].provenance[0].evidence, "commit the result")
        self.assertEqual((spec.vocabulary_version, spec.vocabulary_hash), ("v1", _HASH))
        self.assertEqual(len(llm.requests), 1)

    def test_prompt_shows_declarations_but_no_resource_identity(self) -> None:
        llm = _Scripted(_answer({"option": 1, "evidence": "commit"}))
        GroundedTaskSpecExtractor(llm).extract(_GOAL, _catalog())
        system = llm.requests[0][0][0].content

        self.assertIn("3. action=sort entity_type=repository scope=workspace output_type=state mode=effect", system)
        for hidden in ("tool.test", "Resource ", "repo.write", "repo.commit"):
            self.assertNotIn(hidden, system)

    def test_extracted_spec_lets_the_selector_choose_the_declaring_resources(self) -> None:
        catalog = _catalog()
        llm = _Scripted(_answer({"option": 3, "evidence": "Sort"}, {"option": 1, "evidence": "commit"}))
        spec = GroundedTaskSpecExtractor(llm).extract(_GOAL, catalog)
        selector = GoalAwareSetSelector(lambda _goal: spec)
        results = [SearchResult(resource, 0.9, (), {"relevance": 0.9}) for resource in catalog]

        granted = selector.select(
            results, context=SelectionContext(task=_GOAL, granted_permissions=("repo.write", "repo.commit"))
        )
        missing = selector.select(results, context=SelectionContext(task=_GOAL, granted_permissions=("repo.write",)))

        self.assertEqual(granted.status, "selected")
        self.assertEqual(
            {result.resource.metadata.id for result in granted.results}, {"tool.test.sort", "tool.test.commit"}
        )
        self.assertEqual(missing.status, "escalate")
        self.assertEqual(missing.missing_permissions, ("repo.commit",))

    def test_unmet_capability_and_ambiguity_make_the_spec_uncertain(self) -> None:
        for answer in (
            _answer({"option": 3, "evidence": "Sort"}, unmet=["upload the file to a server"]),
            _answer({"option": 3, "evidence": "Sort"}, ambiguities=["which file is meant"]),
        ):
            with self.subTest(answer=answer):
                spec = GroundedTaskSpecExtractor(_Scripted(answer)).extract(_GOAL, _catalog())
                self.assertEqual(len(spec.unknown_items), 1)
                selector = GoalAwareSetSelector(lambda _goal, spec=spec: spec)
                results = [SearchResult(resource, 0.9, (), {"relevance": 0.9}) for resource in _catalog()]
                self.assertEqual(selector.select(results, context=SelectionContext(task=_GOAL)).status, "abstain")

    def test_invalid_number_or_citation_is_unknown_not_repaired(self) -> None:
        cases = {
            "number out of range": {"option": 9, "evidence": "Sort"},
            "number is a boolean": {"option": True, "evidence": "Sort"},
            "citation absent": {"option": 3, "evidence": "Order the names"},
            "entry malformed": "sort",
        }
        for label, entry in cases.items():
            with self.subTest(label):
                spec = GroundedTaskSpecExtractor(_Scripted(_answer(entry))).extract(_GOAL, _catalog())
                self.assertTrue(spec.unknown_items)
                self.assertIsNone(spec.expression)

    def test_empty_answer_missing_tool_call_and_provider_failure_are_unknown(self) -> None:
        for llm in (
            _Scripted(_answer()),
            _Scripted(content="I would sort the file."),
            _Scripted(error=RuntimeError("boom")),
            _Scripted({"requirements": "none", "unmet": [], "ambiguities": []}),
        ):
            with self.subTest(llm=llm.arguments or llm.content or "error"):
                spec = GroundedTaskSpecExtractor(llm).extract(_GOAL, _catalog())
                self.assertTrue(spec.unknown_items)
                self.assertEqual(len(llm.requests), 1)

    def test_no_model_call_without_a_usable_menu_or_goal(self) -> None:
        mixed = [
            _definition("tool.test.a", [("read", "file", "record", "information")]),
            _definition("tool.test.b", [("sort", "file", "state", "effect")], binding=("v2", "b" * 64)),
        ]
        for goal, resources in ((_GOAL, []), (_GOAL, mixed), ("  ", _catalog())):
            llm = _Scripted(_answer({"option": 1, "evidence": "Sort"}))
            spec = GroundedTaskSpecExtractor(llm).extract(goal, resources)
            self.assertTrue(spec.unknown_items)
            self.assertEqual(llm.requests, [])

    def test_configured_binding_must_match_the_menu(self) -> None:
        llm = _Scripted(_answer({"option": 1, "evidence": "commit"}))
        extractor = GroundedTaskSpecExtractor(llm, vocabulary_version="v9", vocabulary_hash="c" * 64)
        self.assertTrue(extractor.extract(_GOAL, _catalog()).unknown_items)
        self.assertEqual(llm.requests, [])

    def test_duplicate_choices_are_merged(self) -> None:
        llm = _Scripted(_answer({"option": 3, "evidence": "Sort"}, {"option": 3, "evidence": "names"}))
        self.assertEqual(len(_leaves(GroundedTaskSpecExtractor(llm).extract(_GOAL, _catalog()))), 1)


class UngroundedExtractionTest(unittest.TestCase):
    def _extractor(self, llm: LLMProvider, **options: Any) -> GroundedTaskSpecExtractor:
        return GroundedTaskSpecExtractor(
            llm, vocabulary=_VOCABULARY, vocabulary_version="v1", vocabulary_hash=_HASH, **options
        )

    def test_without_a_menu_the_model_writes_fields_from_the_vocabulary(self) -> None:
        llm = _Scripted(
            _answer(
                {
                    "action": "sort", "entity_type": "file", "target_scope": "workspace",
                    "output_type": "state", "mode": "effect", "evidence": "Sort work/names.txt",
                }
            )
        )
        spec = self._extractor(llm).extract(_GOAL)

        self.assertEqual(spec.unknown_items, ())
        self.assertEqual(_leaves(spec)[0].entity_type, "file")
        schema = llm.requests[0][1][0].input_schema["properties"]["requirements"]["items"]
        self.assertEqual(schema["properties"]["action"]["enum"], list(_VOCABULARY["action"]))

    def test_out_of_vocabulary_value_or_empty_scope_is_unknown(self) -> None:
        base = {
            "action": "sort", "entity_type": "file", "target_scope": "workspace",
            "output_type": "state", "mode": "effect", "evidence": "Sort",
        }
        for change in ({"action": "order"}, {"target_scope": " "}, {"mode": "context"}, {"output_type": None}):
            with self.subTest(change=change):
                spec = self._extractor(_Scripted(_answer({**base, **change}))).extract(_GOAL)
                self.assertTrue(spec.unknown_items)

    def test_incomplete_vocabulary_makes_no_model_call(self) -> None:
        llm = _Scripted(_answer())
        spec = GroundedTaskSpecExtractor(llm, vocabulary={"action": ("sort",)}).extract(_GOAL)
        self.assertTrue(spec.unknown_items)
        self.assertEqual(llm.requests, [])

    def test_instructions_differ_from_the_grounded_ones_only_in_the_choice_rule(self) -> None:
        extractor = self._extractor(_Scripted(), scope_guidance="Use workspace for local items.")
        grounded = extractor.instructions(affordance_menu(_catalog())).split("\n")
        ungrounded = extractor.instructions(None).split("\n")

        self.assertEqual(grounded[:3], ungrounded[:3])
        self.assertIn("Use workspace for local items.", ungrounded[3])
        self.assertTrue(grounded[3].startswith("2. Choose each capability from the numbered"))
        self.assertEqual(
            grounded[4].replace("the numbered capability list below", "the vocabulary below"), ungrounded[4]
        )
        self.assertEqual(grounded[5], ungrounded[5])

    def test_prerequisite_switch_and_conventions_change_only_their_own_text(self) -> None:
        menu = affordance_menu(_catalog())
        default = GroundedTaskSpecExtractor(_Scripted()).instructions(menu)
        stated_only = GroundedTaskSpecExtractor(_Scripted(), infer_prerequisites=False).instructions(menu)
        with_conventions = GroundedTaskSpecExtractor(_Scripted(), conventions="Known conventions: X").instructions(menu)

        self.assertIn("necessary to carry those out correctly", default)
        self.assertNotIn("necessary to carry those out correctly", stated_only)
        self.assertEqual(
            stated_only,
            default.replace(
                ", and the operations that are necessary to carry those out correctly, such as inspecting an "
                "input before changing it, checking a result the request says must hold, or preparing "
                "a change before it can be recorded.",
                ".",
            ),
        )
        self.assertEqual(with_conventions.replace("Known conventions: X\n", ""), default)

    def test_version_and_hash_must_be_given_together(self) -> None:
        with self.assertRaises(ValueError):
            GroundedTaskSpecExtractor(_Scripted(), vocabulary_version="v1")


class _FixedRetriever(Retriever):
    def __init__(self) -> None:
        self.queries: list[Any] = []

    def search(self, registry, query):
        self.queries.append(query)
        return [SearchResult(resource, 0.5, (), {}) for resource in registry.all()][: query.top_k]


class GroundedProviderTest(unittest.TestCase):
    def test_provider_grounds_in_retrieved_candidates_without_a_permission_filter(self) -> None:
        registry = ResourceRegistry()
        registry.extend(_catalog())
        retriever = _FixedRetriever()
        llm = _Scripted(_answer({"option": 1, "evidence": "commit"}))
        provider = GroundedTaskSpecProvider(GroundedTaskSpecExtractor(llm), registry, retriever, top_k=7)

        spec = GoalAwareSetSelector(provider).resolve_task_spec(_GOAL)

        self.assertEqual(spec.unknown_items, ())
        self.assertEqual((retriever.queries[0].task, retriever.queries[0].top_k), (_GOAL, 7))
        self.assertFalse(retriever.queries[0].require_permissions)

    def test_top_k_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            GroundedTaskSpecProvider(GroundedTaskSpecExtractor(_Scripted()), ResourceRegistry(), _FixedRetriever(), top_k=0)


if __name__ == "__main__":
    unittest.main()
