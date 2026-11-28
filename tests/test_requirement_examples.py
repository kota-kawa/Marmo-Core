from __future__ import annotations

import unittest

from marmo_core.requirement_examples import (
    ExampleGuidedTaskSpecProvider,
    RequirementExample,
    example_conventions,
    example_from_results,
    render_conventions,
    resolve_examples,
)
from marmo_core.requirement_grounding import AffordanceOption
from marmo_core.tool_runtime import ToolResult

from tests.test_requirement_grounding import _GOAL, _HASH, _VOCABULARY, _Scripted, _catalog, _definition

_EARLIER = "Order work/log.txt and record it."


class ExampleFromResultsTests(unittest.TestCase):
    def test_keeps_successful_calls_in_first_use_order_without_repeats(self) -> None:
        results = [
            ToolResult("tool.test.read", "1.0.0", "success", {}),
            ToolResult("tool.test.sort", "1.0.0", "error", {}, error="boom"),
            {"agent_id": "agent.test.audit", "status": "success"},
            {"tool_id": "tool.test.read", "status": "success"},
            ToolResult("tool.test.commit", "1.0.0", "dry_run", {}),
        ]
        example = example_from_results(_EARLIER, results)
        self.assertEqual(example, RequirementExample(_EARLIER, ("tool.test.read", "agent.test.audit")))

    def test_a_run_without_a_successful_call_gives_no_example(self) -> None:
        self.assertIsNone(example_from_results(_EARLIER, [ToolResult("tool.test.sort", "1.0.0", "timeout", {})]))
        self.assertIsNone(example_from_results("  ", [ToolResult("tool.test.sort", "1.0.0", "success", {})]))


class ConventionsTests(unittest.TestCase):
    def test_affordances_come_from_the_current_contracts(self) -> None:
        example = RequirementExample(_EARLIER, ("tool.test.sort", "tool.test.commit"))
        text = example_conventions([example], _catalog())
        self.assertIn("- action=sort entity_type=repository target_scope=workspace output_type=state mode=effect", text)
        self.assertIn('Request: "Order work/log.txt and record it."', text)
        self.assertIn("Capabilities: action=sort entity_type=repository target_scope=workspace output_type=state "
                      "mode=effect; action=commit entity_type=commit", text)
        self.assertNotIn("tool.test", text, "resource ids are not shown to the model")
        # The catalog author relabels the sort tool: the same example now teaches the new wording.
        relabelled = [_definition("tool.test.sort", [("sort", "file", "record", "effect")]), *_catalog()[1:]]
        self.assertIn("action=sort entity_type=file target_scope=workspace output_type=record mode=effect",
                      example_conventions([example], relabelled))
        self.assertNotIn("entity_type=repository target_scope=workspace output_type=state",
                         example_conventions([example], relabelled))

    def test_missing_and_unobserved_resources_contribute_nothing(self) -> None:
        catalog = [_catalog()[1], _definition("tool.test.sort", [("sort", "repository", "state", "effect")],
                                              observed=False)]
        examples = [RequirementExample("gone", ("tool.test.removed", "tool.test.sort")),
                    RequirementExample(_EARLIER, ("tool.test.removed", "tool.test.commit"))]
        resolved = resolve_examples(examples, catalog)
        self.assertEqual(resolved, [(_EARLIER, (AffordanceOption("commit", "commit", "workspace", "state", "effect"),))])
        self.assertEqual(example_conventions(examples[:1], catalog), "")

    def test_list_only_rendering_omits_the_worked_examples(self) -> None:
        text = example_conventions([RequirementExample(_EARLIER, ("tool.test.read",))], _catalog(),
                                   worked_examples=False)
        self.assertIn("Capability descriptions seen so far:", text)
        self.assertNotIn("Request:", text)
        self.assertEqual(render_conventions([]), "")


class ProviderTests(unittest.TestCase):
    def test_provider_puts_the_examples_into_the_extraction_prompt(self) -> None:
        llm = _Scripted({
            "requirements": [{"action": "sort", "entity_type": "repository", "target_scope": "workspace",
                              "output_type": "state", "mode": "effect", "evidence": "Sort work/names.txt"}],
            "unmet": [], "ambiguities": [],
        })
        provider = ExampleGuidedTaskSpecProvider(
            llm, [RequirementExample(_EARLIER, ("tool.test.sort",))], _catalog(),
            vocabulary=_VOCABULARY, vocabulary_version="v1", vocabulary_hash=_HASH,
        )
        spec = provider(_GOAL)
        self.assertFalse(spec.unknown_items)
        self.assertEqual(spec.expression.children[0].entity_type, "repository")
        system = llm.requests[0][0][0].content
        self.assertIn('Request: "Order work/log.txt and record it."', system)
        self.assertNotIn("Capability list:", system, "no menu is shown")
        with self.assertRaises(ValueError):
            ExampleGuidedTaskSpecProvider(llm, [], _catalog(), conventions="x")


if __name__ == "__main__":
    unittest.main()
