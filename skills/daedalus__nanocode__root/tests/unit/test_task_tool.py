"""Tests for TaskTool (subagent management)."""

from unittest.mock import MagicMock

import pytest

from nanocode.agents import AgentInfo, AgentMode, AgentRegistry
from nanocode.agents.permission import PermissionHandler
from nanocode.tools.task import SubAgentSession, TaskTool, create_task_tool


@pytest.fixture
def agent_registry():
    """Create a test agent registry."""
    registry = AgentRegistry()
    registry.register(
        AgentInfo(
            name="explore",
            mode=AgentMode.SUBAGENT,
            description="Explore codebase",
        )
    )
    registry.register(
        AgentInfo(
            name="build",
            mode=AgentMode.SUBAGENT,
            description="Build new code",
        )
    )
    return registry


@pytest.fixture
def permission_handler():
    """Create a test permission handler."""
    return PermissionHandler()


@pytest.fixture
def task_tool(agent_registry, permission_handler):
    """Create a test task tool."""
    return TaskTool(
        agent_registry=agent_registry,
        permission_handler=permission_handler,
    )


class TestTaskTool:
    """Test TaskTool functionality."""

    def test_create_task_tool(self, task_tool):
        """Test creating task tool."""
        assert task_tool.name == "task"
        assert "subagent_type" in task_tool.parameters["properties"]

    def test_get_accessible_agents(self, task_tool):
        """Test getting accessible agents."""
        agents = task_tool._get_accessible_agents()

        assert len(agents) == 2
        names = [a.name for a in agents]
        assert "explore" in names
        assert "build" in names

    def test_get_accessible_agents_excludes_primary(self, task_tool, agent_registry):
        """Test that primary agents are excluded."""
        agent_registry.register(
            AgentInfo(name="primary", mode=AgentMode.PRIMARY, description="Main agent")
        )

        agents = task_tool._get_accessible_agents()
        names = [a.name for a in agents]

        assert "primary" not in names

    def test_match_pattern(self, task_tool):
        """Test pattern matching."""
        assert task_tool._match_pattern("*", "anything") is True
        assert task_tool._match_pattern("explore", "explore") is True
        assert task_tool._match_pattern("explore", "build") is False

    def test_build_description(self, task_tool):
        """Test building tool description."""
        desc = task_tool._build_description()

        assert "explore" in desc
        assert "build" in desc

    def test_update_description(self, task_tool):
        """Test updating tool description."""
        task_tool.update_description()
        desc = task_tool.description

        assert "explore" in desc

    def test_set_parent_agent(self, task_tool):
        """Test setting parent agent."""
        parent = MagicMock()
        parent.current_agent = MagicMock(name="plan")

        task_tool.set_parent_agent(parent)

        assert task_tool._parent_agent == parent


class TestSubAgentSession:
    """Test SubAgentSession dataclass."""

    def test_create_session(self):
        """Test creating a session."""
        agent = AgentInfo(
            name="explore", mode=AgentMode.SUBAGENT, description="Explore"
        )
        session = SubAgentSession(id="session-123", agent=agent)

        assert session.id == "session-123"
        assert session.agent.name == "explore"
        assert session.completed is False
        assert session.result is None
        assert session.parent_session_id is None

    def test_session_with_parent_id(self):
        """Test session with parent session ID."""
        agent = AgentInfo(
            name="explore", mode=AgentMode.SUBAGENT, description="Explore"
        )
        session = SubAgentSession(
            id="session-123",
            agent=agent,
            parent_session_id="parent-abc",
        )

        assert session.parent_session_id == "parent-abc"

    def test_mark_completed(self):
        """Test marking session as completed."""
        agent = AgentInfo(
            name="explore", mode=AgentMode.SUBAGENT, description="Explore"
        )
        session = SubAgentSession(id="session-123", agent=agent)
        session.completed = True
        session.result = "Task done!"

        assert session.completed is True
        assert session.result == "Task done!"


class TestCreateTaskTool:
    """Test create_task_tool factory function."""

    def test_create_task_tool_factory(self, agent_registry, permission_handler):
        """Test factory function."""
        tool = create_task_tool(agent_registry, permission_handler)

        assert isinstance(tool, TaskTool)
        assert tool.name == "task"
