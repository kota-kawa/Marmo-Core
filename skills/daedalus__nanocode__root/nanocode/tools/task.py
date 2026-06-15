"""Task tool for launching subagents."""

import logging
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from nanocode.agents import (
    AgentInfo,
    AgentMode,
    AgentRegistry,
    PermissionAction,
)
from nanocode.agents.permission import PermissionHandler
from nanocode.tools import Tool, ToolResult

if TYPE_CHECKING:
    from nanocode.core import AutonomousAgent

logger = logging.getLogger("nanocode.task")

TASK_DESCRIPTION = """Launch a new agent to handle complex, multistep tasks autonomously.

Available agent types and the tools they have access to:
{agents}

When using the Task tool, you must specify a subagent_type parameter to select which agent type to use.

When to use the Task tool:
- When you are instructed to execute custom slash commands. Use the Task tool with the slash command invocation as the entire prompt.
- When you need to explore a codebase or find information that requires multiple searches
- When you need to perform research that involves multiple steps

When NOT to use the Task tool:
- If you want to read a specific file path, use the Read or Glob tool instead
- If you are searching for a specific class definition like "class Foo", use the Glob tool instead
- If you are searching for code within a specific file or set of 2-3 files, use the Read tool instead
- Other tasks that are not related to the agent descriptions above


Usage notes:
1. Launch multiple agents concurrently whenever possible, to maximize performance
2. When the agent is done, it will return a single message back to you
3. Each agent invocation starts with a fresh context unless you provide task_id to resume
4. The agent's outputs should generally be trusted
5. Clearly tell the agent whether you expect it to write code or just to do research
"""


@dataclass
class SubAgentSession:
    """Represents a subagent session."""

    id: str
    agent: AgentInfo
    messages: list = field(default_factory=list)
    parent_session_id: str | None = None
    completed: bool = False
    result: str | None = None


class TaskTool(Tool):
    """Tool for launching subagents to handle tasks."""

    def __init__(
        self,
        agent_registry: AgentRegistry,
        permission_handler: PermissionHandler,
    ):
        self.nanocode_registry = agent_registry
        self.permission_handler = permission_handler
        self.sessions: dict[str, SubAgentSession] = {}
        self._parent_agent: AutonomousAgent | None = None
        logger.debug("TaskTool initialized")

        description = self._build_description()

        super().__init__(
            name="task",
            description=description,
            parameters={
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "A short (3-5 words) description of the task",
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The task for the agent to perform",
                    },
                    "subagent_type": {
                        "type": "string",
                        "description": "The type of specialized agent to use for this task (e.g., 'explore', 'general')",
                    },
                    "task_id": {
                        "type": "string",
                        "description": "Optional task ID to resume a previous task session",
                    },
                },
                "required": ["description", "prompt", "subagent_type"],
            },
        )

    def set_parent_agent(self, agent: "AutonomousAgent"):
        """Set the parent agent for spawning subagents."""
        self._parent_agent = agent
        logger.debug(
            f"TaskTool: Parent agent set to '{agent.current_agent.name if agent.current_agent else None}'"
        )

    def _get_accessible_agents(
        self, caller: AgentInfo | None = None
    ) -> list[AgentInfo]:
        """Get agents accessible to the caller based on permissions."""
        all_agents = [
            a for a in self.nanocode_registry.list() if a.mode != AgentMode.PRIMARY
        ]

        if caller is None:
            logger.debug(
                f"_get_accessible_agents(caller=None) -> {len(all_agents)} agents"
            )
            return all_agents

        accessible = []
        for agent in all_agents:
            action = self._evaluate_task_permission(caller, agent.name)
            if action != PermissionAction.DENY:
                accessible.append(agent)
        logger.debug(
            f"_get_accessible_agents(caller={caller.name}) -> {len(accessible)} agents"
        )
        return accessible

    def _evaluate_task_permission(
        self, caller: AgentInfo, subagent_name: str
    ) -> PermissionAction:
        """Evaluate if caller can invoke a specific subagent."""
        for rule in caller.permission:
            if rule.permission == "task":
                if self._match_pattern(rule.pattern, subagent_name):
                    logger.debug(
                        f"_evaluate_task_permission({caller.name}, {subagent_name}) -> {rule.action.value}"
                    )
                    return rule.action
        logger.debug(
            f"_evaluate_task_permission({caller.name}, {subagent_name}) -> ASK (default)"
        )
        return PermissionAction.ASK

    def _match_pattern(self, pattern: str, value: str) -> bool:
        """Match a pattern against a value using wildcards."""
        import fnmatch

        if pattern == "*":
            return True
        result = fnmatch.fnmatch(value, pattern)
        logger.debug(f"_match_pattern('{pattern}', '{value}') -> {result}")
        return result

    def _build_description(self, caller: AgentInfo | None = None) -> str:
        """Build the tool description with available agents."""
        accessible_agents = self._get_accessible_agents(caller)

        agent_list = []
        for a in accessible_agents:
            desc = (
                a.description
                or "This subagent should only be called manually by the user."
            )
            agent_list.append(f"- {a.name}: {desc}")

        agents_text = "\n".join(agent_list)
        logger.debug(
            f"_build_description(caller={caller.name if caller else None}) -> {len(accessible_agents)} agents"
        )
        return TASK_DESCRIPTION.replace("{agents}", agents_text)

    def update_description(self, caller: AgentInfo | None = None):
        """Update the tool description based on caller's permissions."""
        logger.debug(f"update_description(caller={caller.name if caller else None})")
        self.description = self._build_description(caller)

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the task tool to launch a subagent."""
        description = kwargs.get("description", "")
        prompt = kwargs.get("prompt", "")
        subagent_type = kwargs.get("subagent_type", "")
        task_id = kwargs.get("task_id")

        logger.info(
            f"TaskTool.execute: description={description}, subagent_type={subagent_type}, task_id={task_id}"
        )
        logger.debug(f"TaskTool.execute: prompt={prompt[:100]}...")

        subagent = self.nanocode_registry.get(subagent_type)
        if not subagent:
            logger.warning(f"TaskTool: Unknown agent type '{subagent_type}'")
            return ToolResult(
                success=False,
                content=None,
                error=f"Unknown agent type: {subagent_type} is not a valid agent type. Available: {[a.name for a in self.nanocode_registry.list() if a.mode != AgentMode.PRIMARY]}",
            )

        session_id = (
            task_id if task_id and task_id in self.sessions else str(uuid.uuid4())
        )

        if session_id not in self.sessions:
            session = SubAgentSession(
                id=session_id,
                agent=subagent,
            )
            self.sessions[session_id] = session
            logger.info(
                f"TaskTool: Created new session {session_id} for agent '{subagent_type}'"
            )

        session = self.sessions[session_id]

        if session.completed and not task_id:
            logger.info(
                f"TaskTool: Session {session_id} already completed, returning cached result"
            )
            return ToolResult(
                success=True,
                content=session.result,
                metadata={
                    "session_id": session_id,
                    "description": description,
                    "subagent_type": subagent_type,
                    "completed": True,
                },
            )

        if self._parent_agent is None:
            logger.warning("TaskTool: No parent agent set, cannot execute subagent")
            return ToolResult(
                success=True,
                content=f"Subagent session {session_id} created for '{subagent_type}' but parent agent not configured. Use task_id to resume later.",
                metadata={
                    "session_id": session_id,
                    "description": description,
                    "subagent_type": subagent_type,
                },
            )

        old_agent = self._parent_agent.current_agent
        try:
            logger.info(
                f"TaskTool: Switching to subagent '{subagent.name}' for session {session_id}"
            )
            self._parent_agent.switch_agent(subagent.name)

            logger.info(
                f"TaskTool: Executing prompt with {subagent.name}: {prompt[:100]}..."
            )
            result = await self._parent_agent.process_input(
                prompt,
                show_thinking=False,
                show_messages=False,
            )

            session.result = result
            session.completed = True
            result_len = len(result) if result else 0
            logger.info(
                f"TaskTool: Subagent '{subagent.name}' completed, result length: {result_len}"
            )

            return ToolResult(
                success=True,
                content=result,
                metadata={
                    "session_id": session_id,
                    "description": description,
                    "subagent_type": subagent_type,
                    "completed": True,
                },
            )

        finally:
            if old_agent:
                logger.info(
                    f"TaskTool: Switching back to parent agent '{old_agent.name}'"
                )
                self._parent_agent.switch_agent(old_agent.name)


def create_task_tool(
    agent_registry: AgentRegistry, permission_handler: PermissionHandler
) -> TaskTool:
    """Create and configure the task tool."""
    return TaskTool(
        agent_registry=agent_registry,
        permission_handler=permission_handler,
    )
