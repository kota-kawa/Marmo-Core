from __future__ import annotations

import unittest

from marmo_core import (
    AgentInterface,
    BoundTool,
    ContextCompiler,
    InjectedMemory,
    LoadedSkill,
    ResourceDefinition,
)


def _definition(
    resource_id: str,
    kind: str,
    *,
    version: str = "1.0.0",
    dependencies: tuple[str, ...] = (),
    **extras,
) -> ResourceDefinition:
    data = {
        "id": resource_id,
        "kind": kind,
        "name": resource_id,
        "version": version,
        "description": f"{kind} description for {resource_id}",
        "capabilities": ["compiler dependency test"],
        "input_summary": "input summary",
        "output_summary": "output summary",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": f"{kind}://{resource_id}",
        "tags": ["compiler"],
        "dependencies": list(dependencies),
    }
    data.update(extras)
    return ResourceDefinition.from_mapping(data)


def _tool(resource_id: str, dependencies: tuple[str, ...] = ()) -> BoundTool:
    definition = _definition(
        resource_id,
        "tool",
        dependencies=dependencies,
        input_schema={"type": "object", "properties": {}},
    )
    return BoundTool(definition, dict(definition.extras["input_schema"]), {}, lambda: None)


def _skill(
    resource_id: str,
    instructions: str,
    *,
    version: str = "1.0.0",
    dependencies: tuple[str, ...] = (),
) -> LoadedSkill:
    definition = _definition(
        resource_id,
        "skill",
        version=version,
        dependencies=dependencies,
    )
    return LoadedSkill(definition, instructions)


class ContextCompilerDependencyTests(unittest.TestCase):
    def test_observed_context_dependencies_are_atomic(self) -> None:
        tool = _tool("tool.lookup")
        contract = {"schema_version": 1, "observed": True, "complete": True,
                    "source_evidence": [{"source": "fixture", "evidence": "requires procedure"}],
                    "context": {"all_of": ["skill.rules"]}}
        tool = BoundTool(ResourceDefinition(tool.definition.metadata,
            {**tool.definition.extras, "routing_contract": contract}), tool.input_schema, {}, tool.handler)
        skill = _skill("skill.rules", "critical rule " * 400)
        budget = max(ContextCompiler().compile("lookup", tools=[tool]).estimated_tokens,
                     ContextCompiler().compile("lookup").estimated_tokens) + 3
        compiled = ContextCompiler(preserve_dependencies=True).compile(
            "lookup", tools=[tool], skills=[skill], token_budget=budget)
        self.assertEqual(compiled.tools, ())

    def test_one_of_context_can_use_an_available_alternative(self) -> None:
        tool = _tool("tool.lookup")
        contract = {"schema_version": 1, "observed": True, "complete": True,
                    "source_evidence": [{"source": "fixture", "evidence": "requires procedure"}],
                    "context": {"one_of": [["missing", "skill.rules"]]}}
        tool = BoundTool(ResourceDefinition(tool.definition.metadata,
            {**tool.definition.extras, "routing_contract": contract}), tool.input_schema, {}, tool.handler)
        skill = _skill("skill.rules", "critical rule")
        compiled = ContextCompiler(preserve_dependencies=True).compile("lookup", tools=[tool], skills=[skill])
        self.assertEqual(set(compiled.resource_ids), {"tool.lookup@1.0.0", "skill.rules@1.0.0"})

    def test_skill_dependency_is_preserved_too(self) -> None:
        skill = _skill("skill.rules", "critical rule", dependencies=("memory.facts",))
        memory = InjectedMemory(_definition("memory.facts", "memory"), "essential fact " * 400)
        budget = max(ContextCompiler().compile("lookup", skills=[skill]).estimated_tokens,
                     ContextCompiler().compile("lookup").estimated_tokens) + 3
        compiled = ContextCompiler(preserve_dependencies=True).compile(
            "lookup", memories=[memory], skills=[skill], token_budget=budget)
        self.assertNotIn(skill.metadata.identity, compiled.resource_ids)
        self.assertEqual(compiled.trimmed_resource_ids, ())

    def test_default_mode_keeps_legacy_callable_when_dependency_is_missing(self) -> None:
        tool = _tool("tool.lookup", ("skill.unavailable",))

        compiled = ContextCompiler().compile("look it up", tools=[tool])

        self.assertEqual([item.name for item in compiled.tools], ["tool.lookup"])

    def test_budget_that_fits_only_tool_omits_tool_with_oversized_skill_dependency(self) -> None:
        tool = _tool("tool.lookup", ("skill.lookup-rules",))
        skill = _skill("skill.lookup-rules", "critical rule " * 400)
        legacy_tool_only = ContextCompiler().compile("look it up", tools=[tool])
        no_tools = ContextCompiler().compile("look it up")

        compiled = ContextCompiler(
            preserve_dependencies=True,
            token_budget=max(legacy_tool_only.estimated_tokens, no_tools.estimated_tokens),
        ).compile("look it up", tools=[tool], skills=[skill])

        self.assertEqual(compiled.tools, ())
        self.assertIn(tool.metadata.identity, compiled.omitted_resource_ids)
        self.assertIn(skill.metadata.identity, compiled.omitted_resource_ids)

    def test_missing_or_version_mismatched_dependency_never_leaves_dangling_tool(self) -> None:
        available = _skill("skill.lookup-rules", "rules", version="1.0.0")
        for dependency in ("skill.unavailable", "skill.lookup-rules@2.0.0"):
            with self.subTest(dependency=dependency):
                tool = _tool("tool.lookup", (dependency,))

                compiled = ContextCompiler(preserve_dependencies=True).compile(
                    "look it up",
                    tools=[tool],
                    skills=[available],
                )

                self.assertEqual(compiled.tools, ())
                self.assertIn(tool.metadata.identity, compiled.omitted_resource_ids)

    def test_dependency_memory_is_not_trimmed_to_make_callable_fit(self) -> None:
        memory_definition = _definition("memory.rules", "memory")
        memory = InjectedMemory(memory_definition, "required detail " * 300)
        tool = _tool("tool.lookup", (memory.metadata.identity,))
        tool_only = ContextCompiler().compile("look it up", tools=[tool])

        compiled = ContextCompiler(
            preserve_dependencies=True,
            token_budget=tool_only.estimated_tokens + 35,
        ).compile("look it up", memories=[memory], tools=[tool])

        self.assertEqual(compiled.tools, ())
        self.assertNotIn(memory.metadata.identity, compiled.trimmed_resource_ids)
        self.assertIn(memory.metadata.identity, compiled.omitted_resource_ids)

    def test_memory_without_dependencies_keeps_legacy_trimming(self) -> None:
        memory = InjectedMemory(
            _definition("memory.notes", "memory"),
            "reference detail " * 300,
        )
        compiler = ContextCompiler(preserve_dependencies=True)
        base = compiler.compile("summarize notes")
        full = compiler.compile("summarize notes", memories=[memory])
        budget = base.estimated_tokens + max(
            40,
            (full.estimated_tokens - base.estimated_tokens) // 3,
        )

        compiled = ContextCompiler(
            preserve_dependencies=True,
            token_budget=budget,
        ).compile("summarize notes", memories=[memory])

        self.assertIn(memory.metadata.identity, compiled.resource_ids)
        self.assertEqual(compiled.trimmed_resource_ids, (memory.metadata.identity,))
        self.assertLessEqual(compiled.estimated_tokens, budget)

    def test_shared_dependency_is_counted_once_for_multiple_tools(self) -> None:
        shared = _skill("skill.common", "shared guidance " * 30)
        first = _tool("tool.first", (shared.metadata.identity,))
        second = _tool("tool.second", (shared.metadata.identity,))
        compiler = ContextCompiler(preserve_dependencies=True)
        complete = compiler.compile(
            "use both",
            skills=[shared],
            tools=[first, second],
        )

        compiled = ContextCompiler(
            preserve_dependencies=True,
            token_budget=complete.estimated_tokens,
        ).compile("use both", skills=[shared], tools=[first, second])

        self.assertEqual(
            {item.name for item in compiled.tools},
            {"tool.first", "tool.second"},
        )
        self.assertEqual(compiled.resource_ids.count(shared.metadata.identity), 1)

    def test_version_qualified_dependency_selects_exact_version(self) -> None:
        older = _skill("skill.rules", "older rules", version="1.0.0")
        selected = _skill("skill.rules", "selected rules", version="2.0.0")
        tool = _tool("tool.apply-rules", (selected.metadata.identity,))
        compiler = ContextCompiler(preserve_dependencies=True)
        exact_closure = compiler.compile("apply rules", skills=[selected], tools=[tool])

        compiled = ContextCompiler(
            preserve_dependencies=True,
            token_budget=exact_closure.estimated_tokens,
        ).compile("apply rules", skills=[older, selected], tools=[tool])

        self.assertEqual([item.name for item in compiled.tools], ["tool.apply-rules"])
        self.assertIn(selected.metadata.identity, compiled.resource_ids)
        self.assertNotIn(older.metadata.identity, compiled.resource_ids)

    def test_unqualified_dependency_is_ambiguous_across_versions(self) -> None:
        older = _skill("skill.rules", "older rules", version="1.0.0")
        newer = _skill("skill.rules", "newer rules", version="2.0.0")
        tool = _tool("tool.apply-rules", ("skill.rules",))

        compiled = ContextCompiler(preserve_dependencies=True).compile(
            "apply rules",
            skills=[older, newer],
            tools=[tool],
        )

        self.assertEqual(compiled.tools, ())
        self.assertIn(tool.metadata.identity, compiled.omitted_resource_ids)

    def test_dependency_cycle_invalidates_callable_closure(self) -> None:
        tool_definition = _definition(
            "tool.call",
            "tool",
            dependencies=("skill.helper",),
            input_schema={"type": "object", "properties": {}},
        )
        tool = BoundTool(
            tool_definition,
            dict(tool_definition.extras["input_schema"]),
            {},
            lambda: None,
        )
        cyclic_skill = _skill("skill.helper", "helper", dependencies=(tool.metadata.id,))

        compiled = ContextCompiler(preserve_dependencies=True).compile(
            "call helper",
            skills=[cyclic_skill],
            tools=[tool],
        )

        self.assertEqual(compiled.tools, ())
        self.assertIn(tool.metadata.identity, compiled.omitted_resource_ids)

    def test_agent_dependencies_are_budgeted_as_a_closure(self) -> None:
        skill = _skill("skill.delegate-rules", "delegate carefully")
        agent_definition = _definition(
            "agent.delegate",
            "agent",
            dependencies=(skill.metadata.identity,),
            agent_card={
                "input_schema": {
                    "type": "object",
                    "required": ["goal"],
                    "properties": {"goal": {"type": "string"}},
                }
            },
        )
        agent = AgentInterface.from_definition(agent_definition)
        agent_only = ContextCompiler().compile("delegate this", agents=[agent])
        no_tools = ContextCompiler().compile("delegate this")
        complete = ContextCompiler(preserve_dependencies=True).compile(
            "delegate this",
            skills=[skill],
            agents=[agent],
        )

        too_small = ContextCompiler(
            preserve_dependencies=True,
            token_budget=max(agent_only.estimated_tokens, no_tools.estimated_tokens),
        ).compile("delegate this", skills=[skill], agents=[agent])
        compiled = ContextCompiler(
            preserve_dependencies=True,
            token_budget=complete.estimated_tokens,
        ).compile("delegate this", skills=[skill], agents=[agent])

        self.assertEqual(too_small.agent_ids, ())
        self.assertEqual(compiled.agent_ids, (agent.metadata.identity,))
        self.assertIn(skill.metadata.identity, compiled.resource_ids)


if __name__ == "__main__":
    unittest.main()
