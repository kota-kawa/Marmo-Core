from __future__ import annotations

import unittest

from marmo_core import (
    AgentInterface,
    BoundTool,
    ContextCompiler,
    InjectedMemory,
    Kernel,
    LoadedSkill,
    LLMResponse,
    MockLLMProvider,
    ResourceDefinition,
    ResourceRegistry,
    ToolCall,
)


def _definition(resource_id: str, kind: str, **extras) -> ResourceDefinition:
    data = {
        "id": resource_id,
        "kind": kind,
        "name": resource_id,
        "version": "1.0.0",
        "description": f"{kind} description for {resource_id}",
        "capabilities": ["compile context"],
        "input_summary": "input summary",
        "output_summary": "output summary",
        "required_permissions": [],
        "cost_estimate": 0.0,
        "latency_class": "fast",
        "side_effect": "none",
        "trust_level": "core",
        "ref": f"{kind}://{resource_id}",
        "tags": ["compiler"],
    }
    data.update(extras)
    return ResourceDefinition.from_mapping(data)


def _activated_resources():
    memory_definition = _definition("memory.notes", "memory", content="reference facts")
    skill_definition = _definition("skill.rules", "skill", instructions="follow the rules")
    tool_definition = _definition(
        "tool.lookup",
        "tool",
        input_schema={
            "type": "object",
            "required": ["query"],
            "properties": {"query": {"type": "string"}},
        },
    )
    agent_definition = _definition(
        "agent.reviewer",
        "agent",
        agent_card={
            "input_schema": {
                "type": "object",
                "required": ["goal"],
                "properties": {"goal": {"type": "string"}},
            }
        },
        delegation_interface="tool_wrap",
    )
    return (
        InjectedMemory(memory_definition, "reference facts"),
        LoadedSkill(skill_definition, "follow the rules"),
        BoundTool(
            tool_definition,
            dict(tool_definition.extras["input_schema"]),
            {},
            lambda query: query,
        ),
        AgentInterface.from_definition(agent_definition),
    )


class ContextCompilerExecutionTests(unittest.TestCase):
    def test_compiles_all_four_resource_kinds(self) -> None:
        memory, skill, tool, agent = _activated_resources()

        compiled = ContextCompiler().compile_execution(
            "review the document",
            memories=[memory],
            skills=[skill],
            tools=[tool],
            agents=[agent],
        )

        self.assertEqual(
            set(compiled.resource_ids),
            {
                "memory.notes@1.0.0",
                "skill.rules@1.0.0",
                "tool.lookup@1.0.0",
                "agent.reviewer@1.0.0",
            },
        )
        self.assertEqual([item.name for item in compiled.tools], ["tool.lookup", "agent.reviewer"])
        self.assertEqual(compiled.agent_ids, ("agent.reviewer@1.0.0",))
        self.assertIn("follow the rules", compiled.system_prompt)
        self.assertIn('trust="untrusted_content"', compiled.system_prompt)

    def test_provider_tool_formats_cover_tools_and_agents(self) -> None:
        memory, skill, tool, agent = _activated_resources()
        compiled = ContextCompiler().compile(
            "review",
            memories=[memory],
            skills=[skill],
            tools=[tool],
            agents=[agent],
        )

        openai = compiled.tool_definitions("openai")
        anthropic = compiled.tool_definitions("anthropic")

        self.assertEqual(openai[0]["type"], "function")
        self.assertEqual(openai[1]["function"]["name"], "agent.reviewer")
        self.assertEqual(anthropic[0]["input_schema"]["type"], "object")
        self.assertEqual(anthropic[1]["name"], "agent.reviewer")
        with self.assertRaisesRegex(ValueError, "provider must be"):
            compiled.tool_definitions("unknown")

    def test_priority_budget_keeps_callable_contracts_before_memory(self) -> None:
        memory, skill, tool, _ = _activated_resources()
        memory = InjectedMemory(memory.definition, "long memory " * 500)
        compiler = ContextCompiler()
        callable_only = compiler.compile("review", tools=[tool])

        compiled = compiler.compile(
            "review",
            memories=[memory],
            skills=[skill],
            tools=[tool],
            token_budget=callable_only.estimated_tokens + 5,
        )

        self.assertEqual([item.name for item in compiled.tools], ["tool.lookup"])
        self.assertIn("memory.notes@1.0.0", compiled.omitted_resource_ids)
        self.assertIn("skill.rules@1.0.0", compiled.omitted_resource_ids)
        self.assertLessEqual(compiled.estimated_tokens, compiled.token_budget)

    def test_memory_is_trimmed_to_the_remaining_budget(self) -> None:
        memory, _, _, _ = _activated_resources()
        memory = InjectedMemory(memory.definition, "0123456789 " * 300)
        compiler = ContextCompiler()
        base = compiler.compile("review")
        full = compiler.compile("review", memories=[memory])
        budget = base.estimated_tokens + max(40, (full.estimated_tokens - base.estimated_tokens) // 3)

        compiled = compiler.compile("review", memories=[memory], token_budget=budget)

        self.assertIn("memory.notes@1.0.0", compiled.resource_ids)
        self.assertEqual(compiled.trimmed_resource_ids, ("memory.notes@1.0.0",))
        self.assertIn("memory truncated to context budget", compiled.system_prompt)
        self.assertLessEqual(compiled.estimated_tokens, budget)

    def test_duplicate_tool_and_agent_callable_names_are_rejected(self) -> None:
        _, _, tool, agent = _activated_resources()
        colliding = AgentInterface(
            agent.definition,
            agent.input_schema,
            callable_name="tool.lookup",
        )

        with self.assertRaisesRegex(ValueError, "duplicate callable name"):
            ContextCompiler().compile("review", tools=[tool], agents=[colliding])


class ContextCompilerSelectionTests(unittest.TestCase):
    def test_selection_stage_contains_only_lightweight_metadata(self) -> None:
        tool = _definition(
            "tool.private",
            "tool",
            input_schema={"type": "object", "properties": {"secret": {"const": "never-show"}}},
            implementation="never-show-handler",
            api_key="never-show-api-key",
        )

        compiled = ContextCompiler().compile_selection(
            "choose a tool",
            [tool],
            granted_permissions=["net.read"],
            per_kind_limits={"tool": 1},
            max_resources=2,
            cost_budget=3.0,
        )
        prompt = "\n".join(message.content for message in compiled.messages)

        self.assertIn("tool.private", prompt)
        self.assertIn("net.read", prompt)
        self.assertIn('"tool": 1', prompt)
        self.assertNotIn("never-show", prompt)
        self.assertNotIn("input_schema", prompt)
        self.assertNotIn('"implementation":', prompt)

    def test_selection_budget_uses_score_or_explicit_priority(self) -> None:
        first = _definition("tool.first", "tool", description="first " * 100)
        second = _definition("tool.second", "tool", description="second " * 100)
        compiler = ContextCompiler()
        first_only = compiler.compile_selection("choose", [first])
        second_only = compiler.compile_selection("choose", [second])

        compiled = compiler.compile_selection(
            "choose",
            [first, second],
            token_budget=max(first_only.estimated_tokens, second_only.estimated_tokens) + 2,
            priorities={"tool.second": 10.0, "tool.first": 1.0},
        )

        self.assertEqual(compiled.resource_ids, ("tool.second@1.0.0",))
        self.assertEqual(compiled.omitted_resource_ids, ("tool.first@1.0.0",))
        self.assertLessEqual(compiled.estimated_tokens, compiled.token_budget)

    def test_too_small_budget_is_educational(self) -> None:
        with self.assertRaisesRegex(ValueError, "too small"):
            ContextCompiler().compile("a goal", token_budget=1)
        with self.assertRaisesRegex(ValueError, "too small"):
            ContextCompiler().compile_selection("a goal", [], token_budget=1)


class KernelCompilerIntegrationTests(unittest.TestCase):
    def test_kernel_audits_budget_and_omitted_resources(self) -> None:
        memory = _definition(
            "memory.large",
            "memory",
            description="large memory for a compiler integration test",
            content="large context " * 500,
        )
        registry = ResourceRegistry()
        registry.add(memory)
        base = ContextCompiler().compile("summarize large memory for a compiler integration test")
        kernel = Kernel(
            registry,
            MockLLMProvider(),
            context_token_budget=base.estimated_tokens + 3,
        )

        result = kernel.run_goal("summarize large memory for a compiler integration test")

        self.assertEqual(result.status, "completed", result.detail)
        record = next(item for item in kernel.audit_log.records if item.kind == "compile")
        self.assertEqual(record.payload["token_budget"], base.estimated_tokens + 3)
        self.assertEqual(record.payload["omitted_resource_ids"], ["memory.large@1.0.0"])

    def test_kernel_reports_an_impossible_budget_as_failure(self) -> None:
        kernel = Kernel(ResourceRegistry(), MockLLMProvider(), context_token_budget=1)

        result = kernel.run_goal("goal")

        self.assertEqual(result.status, "failed")
        self.assertIn("context compilation failed", result.detail)
        self.assertIn("too small", result.detail)

    def test_budget_omitted_tool_cannot_be_called_by_name(self) -> None:
        huge_schema = {
            "type": "object",
            "properties": {
                f"field_{index}": {"type": "string", "description": "large schema field"}
                for index in range(100)
            },
        }
        tool = _definition(
            "tool.large",
            "tool",
            description="large callable for compiler budget test",
            input_schema=huge_schema,
        )
        registry = ResourceRegistry()
        registry.add(tool)
        goal = "use the large callable for compiler budget test"
        base = ContextCompiler().compile(goal)
        llm = MockLLMProvider(
            script=[
                LLMResponse(
                    content="",
                    tool_calls=(ToolCall("call-1", "tool.large", {}),),
                )
            ]
        )
        calls: list[bool] = []
        kernel = Kernel(
            registry,
            llm,
            tool_implementations={"tool.large": lambda: calls.append(True)},
            context_token_budget=base.estimated_tokens + 5,
        )

        result = kernel.run_goal(goal)

        self.assertEqual(result.status, "failed")
        self.assertEqual(calls, [])
        self.assertIn("not available in the compiled context", result.detail)
        compile_record = next(item for item in kernel.audit_log.records if item.kind == "compile")
        self.assertEqual(compile_record.payload["omitted_resource_ids"], ["tool.large@1.0.0"])


if __name__ == "__main__":
    unittest.main()
