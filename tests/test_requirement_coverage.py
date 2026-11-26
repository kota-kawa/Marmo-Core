"""Tests for RequirementCoverageSelector: LLM capability judgment, solver-decided set and status."""

from __future__ import annotations

import json
import unittest

from marmo_core import LLMResponse, MockLLMProvider, ResourceDefinition, SearchResult, SelectionContext
from marmo_core.errors import ProviderError
from marmo_core.llm import LLMProvider
from marmo_core.requirement_coverage import RequirementCoverageSelector, parse_requirements


def _resource(resource_id: str, kind: str = "tool", **overrides) -> ResourceDefinition:
    payload = {
        "id": resource_id, "kind": kind, "name": resource_id, "version": "1.0.0",
        "description": f"resource {resource_id}", "capabilities": [], "input_summary": "in",
        "output_summary": "out", "required_permissions": [], "cost_estimate": 0.0,
        "latency_class": "fast", "side_effect": "none", "trust_level": "core",
        "ref": f"{kind}://{resource_id}", "tags": [],
    }
    payload.update(overrides)
    return ResourceDefinition.from_mapping(payload)


def _results(*definitions: ResourceDefinition) -> list[SearchResult]:
    return [SearchResult(definition, 1.0 - 0.1 * index, (), {"relevance": 1.0 - 0.1 * index})
            for index, definition in enumerate(definitions)]


def _judge(*requirements: tuple[str, list[str]]) -> MockLLMProvider:
    reply = json.dumps({"requirements": [{"need": need, "ids": ids} for need, ids in requirements]})
    return MockLLMProvider(script=[LLMResponse(content=reply)])


def _ids(selection) -> set[str]:
    return {result.resource.metadata.id for result in selection.results}


class FailingLLM(LLMProvider):
    def complete(self, messages, tools=()):
        raise ProviderError("down")


class RequirementCoverageSelectorTests(unittest.TestCase):
    def test_covers_each_requirement_with_one_feasible_unit(self) -> None:
        results = _results(_resource("tool.search"), _resource("tool.search-alt"), _resource("tool.mail"))
        llm = _judge(("search the web", ["tool.search", "tool.search-alt"]), ("send an email", ["tool.mail"]))
        selection = RequirementCoverageSelector(llm).select(results, context=SelectionContext(task="t"))
        self.assertEqual(selection.status, "selected")
        self.assertEqual(_ids(selection), {"tool.search", "tool.mail"})

    def test_per_requirement_all_keeps_every_credited_feasible_unit(self) -> None:
        results = _results(_resource("tool.search"), _resource("tool.search-alt"), _resource("tool.other"))
        llm = _judge(("search the web", ["tool.search", "tool.search-alt"]))
        selection = RequirementCoverageSelector(llm, per_requirement="all").select(
            results, context=SelectionContext(task="t"))
        self.assertEqual(_ids(selection), {"tool.search", "tool.search-alt"})

    def test_a_unit_covering_more_requirements_is_taken_first(self) -> None:
        results = _results(_resource("tool.a"), _resource("tool.b"), _resource("tool.both"))
        llm = _judge(("x", ["tool.a", "tool.both"]), ("y", ["tool.b", "tool.both"]))
        selection = RequirementCoverageSelector(llm).select(results, context=SelectionContext(task="t"))
        self.assertEqual(_ids(selection), {"tool.both"})

    def test_unmet_requirement_abstains_even_when_another_needs_a_grant(self) -> None:
        results = _results(_resource("tool.pay", required_permissions=["payments"]), _resource("tool.misc"))
        llm = _judge(("charge the card", ["tool.pay"]), ("book a flight", []))
        selection = RequirementCoverageSelector(llm).select(results, context=SelectionContext(task="t"))
        self.assertEqual(selection.status, "abstain")
        self.assertIn("book a flight", selection.reason)

    def test_requirement_only_blocked_units_satisfy_escalates_with_fewest_missing(self) -> None:
        results = _results(
            _resource("tool.pay-full", required_permissions=["payments", "admin"]),
            _resource("tool.pay", required_permissions=["payments"]),
            _resource("tool.lookup"),
        )
        llm = _judge(("charge the card", ["tool.pay-full", "tool.pay"]), ("look up the order", ["tool.lookup"]))
        selection = RequirementCoverageSelector(llm).select(results, context=SelectionContext(task="t"))
        self.assertEqual(selection.status, "escalate")
        self.assertEqual(selection.missing_permissions, ("payments",))

    def test_permitted_alternative_avoids_escalation(self) -> None:
        results = _results(_resource("tool.pay", required_permissions=["payments"]), _resource("tool.pay-sandbox"))
        llm = _judge(("charge the card", ["tool.pay", "tool.pay-sandbox"]))
        selection = RequirementCoverageSelector(llm).select(results, context=SelectionContext(task="t"))
        self.assertEqual(selection.status, "selected")
        self.assertEqual(_ids(selection), {"tool.pay-sandbox"})

    def test_judge_prompt_never_shows_permissions_or_costs(self) -> None:
        results = _results(_resource("tool.pay", required_permissions=["payments.secret-scope"], cost_estimate=7.5))
        llm = _judge(("charge the card", ["tool.pay"]))
        RequirementCoverageSelector(llm).select(
            results, context=SelectionContext(task="t", granted_permissions=("other.grant",)))
        prompt = json.dumps(llm.requests[0]["messages"])
        self.assertNotIn("payments.secret-scope", prompt)
        self.assertNotIn("other.grant", prompt)
        self.assertNotIn("7.5", prompt)

    def test_same_candidates_under_different_grants_reuse_one_judgment(self) -> None:
        results = _results(_resource("tool.pay", required_permissions=["payments"]))
        llm = _judge(("charge the card", ["tool.pay"]))
        selector = RequirementCoverageSelector(llm)
        granted = selector.select(results, context=SelectionContext(task="t", granted_permissions=("payments",)))
        blocked = selector.select(results, context=SelectionContext(task="t"))
        self.assertEqual((granted.status, blocked.status), ("selected", "escalate"))
        self.assertEqual(len(llm.requests), 1)

    def test_dependency_closure_comes_from_the_whole_pool(self) -> None:
        skill = _resource("skill.guide", kind="skill")
        tool = _resource("tool.run", dependencies=["skill.guide"])
        results = _results(tool, *[_resource(f"tool.filler{i}") for i in range(3)], skill)
        llm = _judge(("run the job", ["tool.run"]))
        selection = RequirementCoverageSelector(llm, max_candidates=2).select(
            results, context=SelectionContext(task="t"))
        self.assertEqual(_ids(selection), {"tool.run", "skill.guide"})
        self.assertNotIn("skill.guide", json.dumps(llm.requests[0]["messages"]))

    def test_conflicting_cover_respects_conflicts_and_abstains_when_impossible(self) -> None:
        results = _results(_resource("tool.a", conflicts_with=["tool.b"]), _resource("tool.b"))
        llm = _judge(("x", ["tool.a"]), ("y", ["tool.b"]))
        selection = RequirementCoverageSelector(llm).select(results, context=SelectionContext(task="t"))
        self.assertEqual(selection.status, "abstain")
        self.assertIn("constraints", selection.reason)

    def test_failure_abstains_and_is_recorded(self) -> None:
        selector = RequirementCoverageSelector(FailingLLM())
        with self.assertLogs("marmo_core.llm_routing", level="WARNING"):
            selection = selector.select(_results(_resource("tool.a")), context=SelectionContext(task="t"))
        self.assertEqual(selection.status, "abstain")
        self.assertEqual(selector.failures, 1)
        self.assertIsInstance(selector.last_failure, ProviderError)

    def test_reply_without_requirements_abstains(self) -> None:
        selector = RequirementCoverageSelector(MockLLMProvider(script=[LLMResponse(content="I cannot tell.")]))
        with self.assertLogs("marmo_core.llm_routing", level="WARNING"):
            selection = selector.select(_results(_resource("tool.a")), context=SelectionContext(task="t"))
        self.assertEqual(selection.status, "abstain")
        self.assertEqual(selector.failures, 1)

    def test_relevance_floor_applies_before_the_judge(self) -> None:
        llm = _judge(("x", []))
        selection = RequirementCoverageSelector(llm).select(
            _results(_resource("tool.a")), context=SelectionContext(task="t", min_relevance=1.5))
        self.assertEqual(selection.status, "abstain")
        self.assertEqual(llm.requests, [])

    def test_parse_drops_unknown_ids_and_bad_entries(self) -> None:
        text = ('Here: ```json\n{"requirements": [{"need": "x", "ids": ["tool.a", "tool.zzz", "tool.a"]}, '
                '{"need": "", "ids": []}, "junk", {"need": "y", "ids": "tool.a"}]}\n```')
        parsed = parse_requirements(text, ["tool.a"])
        self.assertEqual([(item.need, item.ids) for item in parsed], [("x", ("tool.a",))])
        self.assertEqual(parse_requirements("no json", ["tool.a"]), ())

    def test_parse_takes_the_last_answer_when_the_reply_corrects_itself(self) -> None:
        text = ('{"requirements": [{"need": "x", "ids": ["tool.a", "tool.b"]}]}\n\n'
                'Correction: tool.a cannot do x. Corrected output:\n\n'
                '{"requirements": [{"need": "x", "ids": ["tool.b"]}]}')
        parsed = parse_requirements(text, ["tool.a", "tool.b"])
        self.assertEqual([(item.need, item.ids) for item in parsed], [("x", ("tool.b",))])

    def test_invalid_arguments_are_rejected(self) -> None:
        llm = MockLLMProvider()
        with self.assertRaises(ValueError):
            RequirementCoverageSelector(llm, per_requirement="some")
        with self.assertRaises(ValueError):
            RequirementCoverageSelector(llm, max_candidates=0)


if __name__ == "__main__":
    unittest.main()
