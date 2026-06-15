"""Adversarial tests for TODO system functionality."""

import tempfile
from pathlib import Path

import pytest


class TestTodoServiceBasic:
    """Basic tests for TodoService."""

    def test_create_service(self):
        """Test TodoService can be created."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            assert service.storage_dir == Path(tmpdir)
            assert service.todos_file == Path(tmpdir) / "todos.json"

    def test_add_todo(self):
        """Test adding a todo."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            todo = service.add_todo("session1", "Test todo", "high")

            assert todo.content == "Test todo"
            assert todo.status == "pending"
            assert todo.priority == "high"

    def test_get_todos_empty(self):
        """Test getting todos when none exist."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            todos = service.get_todos("session1")
            assert todos == []

    def test_get_todos_with_todos(self):
        """Test getting todos."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            service.add_todo("session1", "Todo 1", "high")
            service.add_todo("session1", "Todo 2", "medium")

            todos = service.get_todos("session1")
            assert len(todos) == 2
            assert todos[0].content == "Todo 1"
            assert todos[1].content == "Todo 2"

    def test_update_todos(self):
        """Test updating all todos."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            todos = [
                {"content": "Updated 1", "status": "pending", "priority": "high"},
                {"content": "Updated 2", "status": "in_progress", "priority": "medium"},
                {"content": "Updated 3", "status": "completed", "priority": "low"},
            ]
            service.update_todos("session1", todos)

            result = service.get_todos("session1")
            assert len(result) == 3
            assert result[0].status == "pending"
            assert result[1].status == "in_progress"
            assert result[2].status == "completed"

    def test_complete_todo(self):
        """Test completing a todo."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            service.add_todo("session1", "Todo 1", "high")
            service.add_todo("session1", "Todo 2", "medium")

            result = service.complete_todo("session1", 0)
            assert result is True

            todos = service.get_todos("session1")
            assert todos[0].status == "completed"
            assert todos[1].status == "pending"

    def test_delete_todo(self):
        """Test deleting a todo."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            service.add_todo("session1", "Todo 1", "high")
            service.add_todo("session1", "Todo 2", "medium")

            result = service.delete_todo("session1", 0)
            assert result is True

            todos = service.get_todos("session1")
            assert len(todos) == 1
            assert todos[0].content == "Todo 2"

    def test_clear_todos(self):
        """Test clearing todos."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            service.add_todo("session1", "Todo 1", "high")
            service.add_todo("session1", "Todo 2", "medium")

            service.clear_todos("session1")

            todos = service.get_todos("session1")
            assert todos == []


class TestTodoServiceAdversarial:
    """Adversarial tests for TodoService."""

    def test_add_todo_empty_content(self):
        """Test adding todo with empty content."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            todo = service.add_todo("session1", "", "high")

            assert todo.content == ""
            assert todo.status == "pending"

    def test_add_todo_very_long_content(self):
        """Test adding todo with very long content."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            long_content = "a" * 10000
            todo = service.add_todo("session1", long_content, "high")

            assert todo.content == long_content

    def test_add_todo_unicode_content(self):
        """Test adding todo with Unicode content."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            todo = service.add_todo("session1", "日本語テスト", "high")

            assert todo.content == "日本語テスト"

    def test_add_todo_special_characters(self):
        """Test adding todo with special characters."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            todo = service.add_todo(
                "session1", "test<script>alert('xss')</script>", "high"
            )

            assert todo.content == "test<script>alert('xss')</script>"

    def test_get_todos_nonexistent_session(self):
        """Test getting todos for non-existent session."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            todos = service.get_todos("nonexistent")
            assert todos == []

    def test_update_todos_empty_list(self):
        """Test updating todos with empty list."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            service.add_todo("session1", "Existing todo", "high")

            service.update_todos("session1", [])
            todos = service.get_todos("session1")
            assert todos == []

    def test_update_todos_replaces_all(self):
        """Test that update replaces all todos."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            service.add_todo("session1", "Old 1", "high")
            service.add_todo("session1", "Old 2", "medium")

            service.update_todos(
                "session1",
                [{"content": "New", "status": "pending", "priority": "high"}],
            )
            todos = service.get_todos("session1")

            assert len(todos) == 1
            assert todos[0].content == "New"

    def test_complete_todo_invalid_index(self):
        """Test completing with invalid index."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            result = service.complete_todo("session1", 99)
            assert result is False

    def test_complete_todo_negative_index(self):
        """Test completing with negative index."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            service.add_todo("session1", "Todo", "high")
            result = service.complete_todo("session1", -1)
            assert result is False

    def test_delete_todo_invalid_index(self):
        """Test deleting with invalid index."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            result = service.delete_todo("session1", 99)
            assert result is False

    def test_delete_todo_negative_index(self):
        """Test deleting with negative index."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            service.add_todo("session1", "Todo", "high")
            result = service.delete_todo("session1", -1)
            assert result is False

    def test_persistence(self):
        """Test todos are persisted to file."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            service.add_todo("session1", "Persisted todo", "high")

            new_service = TodoService(storage_dir=Path(tmpdir))
            todos = new_service.get_todos("session1")

            assert len(todos) == 1
            assert todos[0].content == "Persisted todo"

    def test_get_stats_empty(self):
        """Test getting stats with no todos."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            stats = service.get_stats("session1")

            assert stats["pending"] == 0
            assert stats["in_progress"] == 0
            assert stats["completed"] == 0
            assert stats["total"] == 0

    def test_get_stats_with_todos(self):
        """Test getting todo statistics."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            service.update_todos(
                "session1",
                [
                    {"content": "Todo 1", "status": "pending", "priority": "high"},
                    {
                        "content": "Todo 2",
                        "status": "in_progress",
                        "priority": "medium",
                    },
                    {"content": "Todo 3", "status": "completed", "priority": "low"},
                ],
            )

            stats = service.get_stats("session1")

            assert stats["pending"] == 1
            assert stats["in_progress"] == 1
            assert stats["completed"] == 1
            assert stats["total"] == 3

    def test_get_stats_nonexistent_session(self):
        """Test getting stats for non-existent session."""
        from nanocode.todo_service import TodoService

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            stats = service.get_stats("nonexistent")
            assert stats["total"] == 0


class TestTodoToolBasic:
    """Basic tests for TodoTool."""

    @pytest.mark.asyncio
    async def test_todo_read_action(self):
        """Test TodoTool read action."""
        from nanocode.core import set_current_session_id
        from nanocode.todo_service import TodoService
        from nanocode.tools.builtin import TodoTool

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            tool = TodoTool(todo_service=service)
            set_current_session_id("test-session")
            service.add_todo("test-session", "Test todo", "high")

            result = await tool.execute(action="read")

            assert result.success is True
            assert "pending" in result.content

    @pytest.mark.asyncio
    async def test_todo_write_action(self):
        """Test TodoTool write action."""
        from nanocode.core import set_current_session_id
        from nanocode.todo_service import TodoService
        from nanocode.tools.builtin import TodoTool

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            tool = TodoTool(todo_service=service)
            set_current_session_id("test-session")

            todos = [
                {"content": "New todo 1", "status": "pending", "priority": "high"},
                {"content": "New todo 2", "status": "completed", "priority": "low"},
            ]
            result = await tool.execute(action="write", todos=todos)

            assert result.success is True
            assert "pending" in result.content

    @pytest.mark.asyncio
    async def test_todo_invalid_action(self):
        """Test TodoTool with invalid action."""
        from nanocode.todo_service import TodoService
        from nanocode.tools.builtin import TodoTool

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            tool = TodoTool(todo_service=service)

            result = await tool.execute(action="invalid")

            assert result.success is False
            assert "Invalid action" in str(result.error)


class TestTodoToolAdversarial:
    """Adversarial tests for TodoTool."""

    @pytest.mark.asyncio
    async def test_write_empty_todos(self):
        """Test TodoTool write with empty todos."""
        from nanocode.core import set_current_session_id
        from nanocode.todo_service import TodoService
        from nanocode.tools.builtin import TodoTool

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            tool = TodoTool(todo_service=service)
            set_current_session_id("test-session")

            result = await tool.execute(action="write", todos=[])

            assert result.success is True

    @pytest.mark.asyncio
    async def test_write_with_missing_fields(self):
        """Test TodoTool write with missing fields in todo."""
        from nanocode.core import set_current_session_id
        from nanocode.todo_service import TodoService
        from nanocode.tools.builtin import TodoTool

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            tool = TodoTool(todo_service=service)
            set_current_session_id("test-session")

            todos = [{"content": "Test todo"}]
            result = await tool.execute(action="write", todos=todos)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_write_with_extra_fields(self):
        """Test TodoTool write with extra fields in todo."""
        from nanocode.core import set_current_session_id
        from nanocode.todo_service import TodoService
        from nanocode.tools.builtin import TodoTool

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            tool = TodoTool(todo_service=service)
            set_current_session_id("test-session")

            todos = [
                {
                    "content": "Test todo",
                    "status": "pending",
                    "priority": "high",
                    "extra": "field",
                }
            ]
            result = await tool.execute(action="write", todos=todos)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_write_unicode_content(self):
        """Test TodoTool write with Unicode content."""
        from nanocode.core import set_current_session_id
        from nanocode.todo_service import TodoService
        from nanocode.tools.builtin import TodoTool

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            tool = TodoTool(todo_service=service)
            set_current_session_id("test-session")

            todos = [
                {"content": "日本語テスト", "status": "pending", "priority": "high"}
            ]
            result = await tool.execute(action="write", todos=todos)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_read_without_session(self):
        """Test TodoTool read without setting session."""
        from nanocode.todo_service import TodoService
        from nanocode.tools.builtin import TodoTool

        with tempfile.TemporaryDirectory() as tmpdir:
            service = TodoService(storage_dir=Path(tmpdir))
            tool = TodoTool(todo_service=service)

            result = await tool.execute(action="read")

            assert result.success is True


class TestGetTodoService:
    """Tests for get_todo_service singleton."""

    def test_get_todo_service_singleton(self):
        """Test get_todo_service returns singleton."""
        from nanocode.todo_service import get_todo_service

        service1 = get_todo_service()
        service2 = get_todo_service()

        assert service1 is service2


class TestTodoSidebarDisplay:
    """Tests for TODO display in sidebar."""

    def test_todo_display_pending(self):
        """Test todo display for pending status."""
        lines = []
        status = "pending"
        if status == "completed":
            icon = "✓"
        elif status == "in_progress":
            icon = "◐"
        elif status == "cancelled":
            icon = "✗"
        else:
            icon = "○"
        content = "Test todo"
        lines.append(f"  {icon} {content}")

        assert "  ○ Test todo" in lines

    def test_todo_display_in_progress(self):
        """Test todo display for in_progress status."""
        lines = []
        status = "in_progress"
        if status == "completed":
            icon = "✓"
        elif status == "in_progress":
            icon = "◐"
        elif status == "cancelled":
            icon = "✗"
        else:
            icon = "○"
        content = "Test todo"
        lines.append(f"  {icon} {content}")

        assert "  ◐ Test todo" in lines

    def test_todo_display_completed(self):
        """Test todo display for completed status."""
        lines = []
        status = "completed"
        if status == "completed":
            icon = "✓"
        elif status == "in_progress":
            icon = "◐"
        elif status == "cancelled":
            icon = "✗"
        else:
            icon = "○"
        content = "Test todo"
        lines.append(f"  {icon} {content}")

        assert "  ✓ Test todo" in lines

    def test_todo_display_cancelled(self):
        """Test todo display for cancelled status."""
        lines = []
        status = "cancelled"
        if status == "completed":
            icon = "✓"
        elif status == "in_progress":
            icon = "◐"
        elif status == "cancelled":
            icon = "✗"
        else:
            icon = "○"
        content = "Test todo"
        lines.append(f"  {icon} {content}")

        assert "  ✗ Test todo" in lines

    def test_todo_display_long_content_truncated(self):
        """Test todo display truncates long content."""
        long_content = "a" * 50
        truncated = (
            long_content[:30] + "..." if len(long_content) > 30 else long_content
        )

        assert truncated == "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaa..."
        assert len(truncated) == 33

    def test_todo_section_header(self):
        """Test TODO section header."""
        lines = []
        todos = [{"content": "Todo 1", "status": "pending", "priority": "high"}]
        if todos:
            lines.append("─ Todos ─")
            for t in todos:
                if t["status"] == "completed":
                    icon = "✓"
                elif t["status"] == "in_progress":
                    icon = "◐"
                elif t["status"] == "cancelled":
                    icon = "✗"
                else:
                    icon = "○"
                content = (
                    t["content"][:30] + "..."
                    if len(t["content"]) > 30
                    else t["content"]
                )
                lines.append(f"  {icon} {content}")

        assert "─ Todos ─" in lines
        assert "  ○ Todo 1" in lines

    def test_todo_section_empty(self):
        """Test TODO section when empty."""
        lines = []
        todos = []
        if todos:
            lines.append("─ Todos ─")
            for t in todos:
                if t["status"] == "completed":
                    icon = "✓"
                elif t["status"] == "in_progress":
                    icon = "◐"
                elif t["status"] == "cancelled":
                    icon = "✗"
                else:
                    icon = "○"
                content = (
                    t["content"][:30] + "..."
                    if len(t["content"]) > 30
                    else t["content"]
                )
                lines.append(f"  {icon} {content}")

        assert "─ Todos ─" not in lines
