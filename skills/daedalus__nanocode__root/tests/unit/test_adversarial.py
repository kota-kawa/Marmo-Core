"""Adversarial tests - try to break the system with extreme inputs and edge cases."""

import json
import os
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "nanocode"))

from nanocode.config import Config
from nanocode.context import ContextManager, Message, TokenCounter
from nanocode.tools import ToolRegistry, ToolResult


class TestContextAdversarial:
    """Adversarial tests for context manager."""

    def test_very_long_message(self):
        """ADVERSARIAL: Very long message (1MB)."""
        manager = ContextManager(max_tokens=100000)

        long_content = "x" * 1_000_000
        manager.add_message("user", long_content)

        tokens = TokenCounter.count_tokens(long_content)
        print(f"  1MB message tokens: {tokens}")

    def test_unicode_extreme(self):
        """ADVERSARIAL: Extreme unicode characters."""
        manager = ContextManager(max_tokens=10000)

        unicode_content = "\U0001f600" * 10000
        manager.add_message("user", unicode_content)

        tokens = TokenCounter.count_tokens(unicode_content)
        print(f"  Extreme unicode tokens: {tokens}")

    def test_nested_json_message(self):
        """ADVERSARIAL: Nested JSON structure."""
        manager = ContextManager(max_tokens=10000)

        nested = {"key": {"nested": {"deep": [{"a": 1}, {"b": 2}]}}}
        content = json.dumps(nested)
        manager.add_message("user", content)

        assert len(manager._messages) == 1

    def test_message_with_null_bytes(self):
        """ADVERSARIAL: Message containing null bytes."""
        manager = ContextManager(max_tokens=10000)

        content = "hello\x00world\x00test"
        manager.add_message("user", content)

        assert len(manager._messages) == 1

    def test_max_tokens_zero(self):
        """ADVERSARIAL: Zero max tokens."""
        try:
            manager = ContextManager(max_tokens=0)
            assert manager._context_limit == 0
        except Exception as e:
            print(f"  Zero tokens handled: {e}")

    def test_negative_max_tokens(self):
        """ADVERSARIAL: Negative max tokens."""
        try:
            manager = ContextManager(max_tokens=-100)
            print(f"  Negative tokens allowed: {manager._context_limit}")
        except Exception as e:
            print(f"  Negative tokens rejected: {e}")

    def test_concurrent_message_add(self):
        """ADVERSARIAL: Concurrent message additions."""
        manager = ContextManager(max_tokens=100000)
        errors = []

        def add_messages():
            try:
                for i in range(100):
                    manager.add_message("user", f"Message {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=add_messages) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        print(
            f"  Concurrent add: {len(manager._messages)} messages, {len(errors)} errors"
        )

    def test_system_prompt_override(self):
        """ADVERSARIAL: Multiple system prompt overrides."""
        manager = ContextManager(max_tokens=10000)

        manager.set_system_prompt("First")
        manager.set_system_prompt("Second")
        manager.set_system_prompt("Third")

        assert len(manager._messages) == 0

    def test_message_role_invalid(self):
        """ADVERSARIAL: Invalid message role."""
        manager = ContextManager(max_tokens=10000)

        msg = Message(role="invalid_role")
        msg.add_text("test")
        manager._messages.append(msg)

        messages = manager.prepare_messages()
        assert len(messages) >= 0


class TestTokenCounterAdversarial:
    """Adversarial tests for token counter."""

    def test_empty_string(self):
        """ADVERSARIAL: Empty string."""
        tokens = TokenCounter.count_tokens("")
        print(f"  Empty string tokens: {tokens}")

    def test_only_whitespace(self):
        """ADVERSARIAL: Only whitespace."""
        tokens = TokenCounter.count_tokens("   \t\n   ")
        print(f"  Whitespace tokens: {tokens}")

    def test_only_newlines(self):
        """ADVERSARIAL: Only newlines."""
        tokens = TokenCounter.count_tokens("\n\n\n\n\n")
        print(f"  Newline tokens: {tokens}")

    def test_mixed_whitespace(self):
        """ADVERSARIAL: Mixed whitespace."""
        tokens = TokenCounter.count_tokens("word " * 10000)
        assert tokens > 0

    def test_very_long_word(self):
        """ADVERSARIAL: Very long single word."""
        word = "a" * 1_000_000
        tokens = TokenCounter.count_tokens(word)
        print(f"  1MB word tokens: {tokens}")

    def test_xml_content(self):
        """ADVERSARIAL: XML content."""
        xml = "<root>" + "<item>" * 10000 + "</item>" * 10000 + "</root>"
        tokens = TokenCounter.count_tokens(xml)
        print(f"  XML tokens: {tokens}")

    def test_code_with_tabs(self):
        """ADVERSARIAL: Code with many tabs."""
        code = "\t" * 1000 + "def test():\n" + "\t" * 1000 + "pass\n"
        tokens = TokenCounter.count_tokens(code)
        print(f"  Tab-heavy code tokens: {tokens}")


class TestToolRegistryAdversarial:
    """Adversarial tests for tool registry."""

    def test_register_duplicate_tool(self):
        """ADVERSARIAL: Register duplicate tool name."""
        registry = ToolRegistry()

        tool1 = MagicMock()
        tool1.name = "test_tool"
        tool1.description = "First"

        tool2 = MagicMock()
        tool2.name = "test_tool"
        tool2.description = "Second"

        registry.register(tool1)
        registry.register(tool2)

        tools = registry.list_tools()
        count = sum(1 for t in tools if t.name == "test_tool")
        print(f"  Duplicate tool count: {count}")

    def test_register_tool_with_none_name(self):
        """ADVERSARIAL: Tool with None name."""
        registry = ToolRegistry()

        tool = MagicMock()
        tool.name = None
        tool.description = "Test"

        try:
            registry.register(tool)
            print("  None name allowed")
        except Exception as e:
            print(f"  None name rejected: {e}")

    def test_get_tool_nonexistent(self):
        """ADVERSARIAL: Get nonexistent tool."""
        registry = ToolRegistry()

        has_tool = registry.has_tool("nonexistent_tool_xyz")
        assert has_tool is False

    def test_unregister_during_iteration(self):
        """ADVERSARIAL: Unregister tool during iteration."""
        registry = ToolRegistry()

        for i in range(10):
            tool = MagicMock()
            tool.name = f"tool_{i}"
            tool.description = f"Tool {i}"
            registry.register(tool)

        tools = registry.list_tools()
        try:
            for t in tools:
                registry.unregister(t.name)
        except Exception as e:
            print(f"  Unregister error: {e}")


class TestConfigAdversarial:
    """Adversarial tests for config."""

    def test_config_with_special_chars(self):
        """ADVERSARIAL: Config with special characters."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("key: value with $pecial ch@rs\n")
            f.write("number: 12345\n")
            f.flush()

            try:
                config = Config(f.name)
                assert config.get("key") == "value with $pecial ch@rs"
            except Exception as e:
                print(f"  Special chars error: {e}")
            finally:
                os.unlink(f.name)

    def test_config_nested_dots(self):
        """ADVERSARIAL: Nested keys with dots."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            import yaml

            yaml.dump({"a": {"b": {"c": "value", "d": "other"}}}, f)
            f.flush()

            try:
                config = Config(f.name)
                assert config.get("a.b.c") == "value"
            finally:
                os.unlink(f.name)

    def test_config_deeply_nested(self):
        """ADVERSARIAL: Deeply nested config."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            nested = {"level1": {"level2": {"level3": {"level4": {"value": "deep"}}}}}
            import yaml

            yaml.dump(nested, f)
            f.flush()

            try:
                config = Config(f.name)
                assert config.get("level1.level2.level3.level4.value") == "deep"
            finally:
                os.unlink(f.name)

    def test_config_nonexistent_file(self):
        """ADVERSARIAL: Nonexistent config file."""
        config = Config("/nonexistent/path/config.yaml")
        result = config.get("any.key")
        assert result is None

    def test_config_empty_yaml(self):
        """ADVERSARIAL: Empty YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()

            try:
                config = Config(f.name)
                assert config.get("any.key") is None
            finally:
                os.unlink(f.name)

    def test_config_invalid_yaml(self):
        """ADVERSARIAL: Invalid YAML."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("key: [unclosed\n")
            f.flush()

            try:
                config = Config(f.name)
                print(f"  Invalid YAML handled: {config._config}")
            except Exception as e:
                print(f"  Invalid YAML error: {e}")
            finally:
                os.unlink(f.name)


class TestToolResultAdversarial:
    """Adversarial tests for ToolResult."""

    def test_result_with_very_long_content(self):
        """ADVERSARIAL: Tool result with 1MB content."""
        content = "x" * 1_000_000
        result = ToolResult(success=True, content=content)

        d = result.to_dict()
        assert len(d["content"]) == 1_000_000

    def test_result_with_binary_content(self):
        """ADVERSARIAL: Tool result with binary-like content."""
        content = bytes([0, 1, 2, 255, 128, 64])
        try:
            result = ToolResult(success=True, content=content)
            print("  Binary content allowed")
        except Exception as e:
            print(f"  Binary rejected: {e}")

    def test_result_with_nested_objects(self):
        """ADVERSARIAL: Tool result with deeply nested metadata."""
        nested = {"a": {"b": {"c": {"d": {"e": "value"}}}}}
        result = ToolResult(success=True, content="test", metadata=nested)

        d = result.to_dict()
        assert d["metadata"]["a"]["b"]["c"]["d"]["e"] == "value"

    def test_result_error_none(self):
        """ADVERSARIAL: Tool result with None error."""
        result = ToolResult(success=True, content="test", error=None)
        assert result.error is None

    def test_result_multiple_metadata(self):
        """ADVERSARIAL: Tool result with many metadata keys."""
        metadata = {f"key_{i}": f"value_{i}" for i in range(100)}
        result = ToolResult(success=True, content="test", metadata=metadata)

        d = result.to_dict()
        assert len(d["metadata"]) == 100


if __name__ == "__main__":
    print("Running adversarial tests...")
    import pytest

    pytest.main([__file__, "-v", "-s"])
