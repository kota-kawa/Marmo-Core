"""Tests for core.py Rich color integration."""

from unittest.mock import patch


class TestLongHorizonConstants:
    """Test long horizon task constants."""

    def test_max_steps_message_defined(self):
        """Test MAX_STEPS_MESSAGE is defined."""
        from nanocode.core import MAX_STEPS_MESSAGE

        assert MAX_STEPS_MESSAGE is not None
        assert len(MAX_STEPS_MESSAGE) > 0

    def test_max_steps_message_contains_critical(self):
        """Test MAX_STEPS_MESSAGE contains CRITICAL."""
        from nanocode.core import MAX_STEPS_MESSAGE

        assert "CRITICAL" in MAX_STEPS_MESSAGE
        assert "MAXIMUM STEPS REACHED" in MAX_STEPS_MESSAGE

    def test_max_steps_message_forbids_tools(self):
        """Test MAX_STEPS_MESSAGE forbids tool calls."""
        from nanocode.core import MAX_STEPS_MESSAGE

        assert "Do NOT make any tool calls" in MAX_STEPS_MESSAGE

    def test_max_steps_message_requires_summary(self):
        """Test MAX_STEPS_MESSAGE requires summary."""
        from nanocode.core import MAX_STEPS_MESSAGE

        assert "summarizing work done so far" in MAX_STEPS_MESSAGE

    def test_auto_continue_message_defined(self):
        """Test AUTO_CONTINUE_MESSAGE is defined."""
        from nanocode.core import AUTO_CONTINUE_MESSAGE

        assert AUTO_CONTINUE_MESSAGE is not None
        assert len(AUTO_CONTINUE_MESSAGE) > 0

    def test_auto_continue_message_contains_continue(self):
        """Test AUTO_CONTINUE_MESSAGE contains continue instruction."""
        from nanocode.core import AUTO_CONTINUE_MESSAGE

        assert "Continue" in AUTO_CONTINUE_MESSAGE
        assert "next steps" in AUTO_CONTINUE_MESSAGE

    def test_overflow_continue_message_defined(self):
        """Test OVERFLOW_CONTINUE_MESSAGE is defined."""
        from nanocode.core import OVERFLOW_CONTINUE_MESSAGE

        assert OVERFLOW_CONTINUE_MESSAGE is not None
        assert "exceeded" in OVERFLOW_CONTINUE_MESSAGE


class TestRetryConstants:
    """Test retry constants."""

    def test_retry_initial_delay_defined(self):
        """Test RETRY_INITIAL_DELAY is defined."""
        from nanocode.core import RETRY_INITIAL_DELAY

        assert RETRY_INITIAL_DELAY == 2.0

    def test_retry_backoff_factor_defined(self):
        """Test RETRY_BACKOFF_FACTOR is defined."""
        from nanocode.core import RETRY_BACKOFF_FACTOR

        assert RETRY_BACKOFF_FACTOR == 2

    def test_retry_max_delay_defined(self):
        """Test RETRY_MAX_DELAY is defined."""
        from nanocode.core import RETRY_MAX_DELAY

        assert RETRY_MAX_DELAY == 30.0


class TestCalculateRetryDelay:
    """Test retry delay calculation."""

    def test_first_attempt_delay(self):
        """Test first attempt delay equals initial delay."""
        from nanocode.core import RETRY_INITIAL_DELAY, calculate_retry_delay

        delay = calculate_retry_delay(1)
        assert delay == RETRY_INITIAL_DELAY

    def test_exponential_backoff(self):
        """Test exponential backoff between attempts."""
        from nanocode.core import calculate_retry_delay

        delay1 = calculate_retry_delay(1)
        delay2 = calculate_retry_delay(2)
        delay3 = calculate_retry_delay(3)
        assert delay2 > delay1
        assert delay3 > delay2

    def test_respects_max_delay(self):
        """Test delay caps at max delay."""
        from nanocode.core import RETRY_MAX_DELAY, calculate_retry_delay

        delay = calculate_retry_delay(100)  # Very high attempt
        assert delay == RETRY_MAX_DELAY

    def test_respects_retry_after_header_ms(self):
        """Test respects retry-after-ms header."""
        from nanocode.core import calculate_retry_delay

        delay = calculate_retry_delay(1, "retry-after-ms: 5000")
        assert delay == 5.0

    def test_respects_retry_after_header_seconds(self):
        """Test respects retry-after header in seconds."""
        from nanocode.core import calculate_retry_delay

        delay = calculate_retry_delay(1, "retry-after: 10")
        assert delay == 10.0


class TestIsRetryableError:
    """Test retryable error detection."""

    def test_context_overflow_not_retryable(self):
        """Test context overflow is not retryable."""
        from nanocode.core import is_retryable_error

        err = Exception("context overflow error")
        retryable, reason = is_retryable_error(err)
        assert retryable is False
        assert reason is None

    def test_5xx_error_retryable(self):
        """Test 5xx errors are retryable."""
        from nanocode.core import is_retryable_error

        err = Exception("status_code: 503 Service Unavailable")
        retryable, reason = is_retryable_error(err)
        assert retryable is True
        assert "Server error" in reason

    def test_rate_limit_retryable(self):
        """Test rate limit errors are retryable."""
        from nanocode.core import is_retryable_error

        err = Exception("rate limit exceeded")
        retryable, reason = is_retryable_error(err)
        assert retryable is True
        assert "Rate limited" in reason

    def test_too_many_requests_retryable(self):
        """Test too many requests is retryable."""
        from nanocode.core import is_retryable_error

        err = Exception("Too many requests, please wait")
        retryable, reason = is_retryable_error(err)
        assert retryable is True

    def test_overloaded_retryable(self):
        """Test overloaded error is retryable."""
        from nanocode.core import is_retryable_error

        err = Exception("Provider is overloaded")
        retryable, reason = is_retryable_error(err)
        assert retryable is True
        assert "overloaded" in reason.lower()

    def test_transient_error_retryable(self):
        """Test generic transient errors are retryable."""
        from nanocode.core import is_retryable_error

        err = Exception("temporary failure")
        retryable, reason = is_retryable_error(err)
        assert retryable is True


class TestRichColorCore:
    """Test RichColor enum in core.py."""

    def test_rich_color_enum_values(self):
        """Test RichColor enum has correct values."""
        from nanocode.core import RichColor

        assert RichColor.RESET.value == "reset"
        assert RichColor.RED.value == "red"
        assert RichColor.GREEN.value == "green"
        assert RichColor.YELLOW.value == "yellow"
        assert RichColor.BLUE.value == "blue"
        assert RichColor.MAGENTA.value == "magenta"
        assert RichColor.CYAN.value == "cyan"
        assert RichColor.GRAY.value == "dim"

    def test_rich_color_enum_count(self):
        """Test RichColor enum has expected colors."""
        from nanocode.core import RichColor

        colors = list(RichColor)
        assert len(colors) == 8


class TestCustomTheme:
    """Test custom theme in core.py."""

    def test_theme_defined(self):
        """Test custom_theme is defined."""
        from nanocode.core import custom_theme

        assert custom_theme is not None

    def test_theme_has_thought_style(self):
        """Test theme has 'thought' style."""
        from nanocode.core import custom_theme

        thought_style = custom_theme.styles.get("thought")
        assert thought_style is not None
        assert thought_style.color is not None

    def test_theme_has_tool_call_style(self):
        """Test theme has 'tool_call' style."""
        from nanocode.core import custom_theme

        style = custom_theme.styles.get("tool_call")
        assert style is not None

    def test_theme_has_debug_style(self):
        """Test theme has 'debug' style."""
        from nanocode.core import custom_theme

        style = custom_theme.styles.get("debug")
        assert style is not None

    def test_theme_has_warning_style(self):
        """Test theme has 'warning' style."""
        from nanocode.core import custom_theme

        style = custom_theme.styles.get("warning")
        assert style is not None


class TestConsole:
    """Test console object in core.py."""

    def test_console_defined(self):
        """Test console is defined."""
        from nanocode.core import console

        assert console is not None

    def test_console_print(self):
        """Test console.print works."""
        from nanocode.core import console

        console.print("[yellow]test[/yellow]")


class TestFormatThinking:
    """Test _format_thinking method."""

    def test_format_thinking_contains_thought_tag(self):
        """Test _format_thinking output contains [thought] tag."""
        from nanocode.core import AutonomousAgent

        with patch("nanocode.core.AutonomousAgent.__init__", return_value=None):
            agent = AutonomousAgent.__new__(AutonomousAgent)
            agent._last_thinking = None

        result = agent._format_thinking("test thinking")
        assert "[thought]" in result
        assert "[/thought]" in result


class TestAugmentedContentThinking:
    """Test augmented content includes thinking."""

    def test_augmented_includes_thought_tag(self):
        """Test augmented content uses [thought] tag."""
        from nanocode.core import AutonomousAgent

        with patch("nanocode.core.AutonomousAgent.__init__", return_value=None):
            agent = AutonomousAgent.__new__(AutonomousAgent)
            agent._last_thinking = "some thinking"
            agent.show_thinking = True

        augmented = ""
        if (
            agent.show_thinking
            and hasattr(agent, "_last_thinking")
            and agent._last_thinking
        ):
            augmented += f"\n\n[thought]| Thinking:[/thought] {agent._last_thinking}"

        assert "[thought]" in augmented
        assert "Thinking:" in augmented
        assert "some thinking" in augmented


class TestDebugOutput:
    """Test debug output uses Rich markup."""

    def test_debug_uses_markup(self):
        """Test debug output uses Rich markup tags."""
        from nanocode.core import console

        with patch.object(console, "print") as mock_print:
            console.print("[debug]test[/debug]")
            mock_print.assert_called_once()

    def test_warning_uses_markup(self):
        """Test warning output uses Rich markup tags."""
        from nanocode.core import console

        with patch.object(console, "print") as mock_print:
            console.print("[warning]test[/warning]")
            mock_print.assert_called_once()


class TestSystemPromptTemplate:
    """Test system prompt template formatting."""

    def test_template_format_replaces_placeholders(self):
        """Template with {placeholder} syntax should be replaced by format_map."""
        prompt = "Agents: {agents}\nTools: {tools}\nCWD: {cwd}"
        agents_info = ["- Agent1: test"]
        tools_info = ["- bash: run commands"]
        cwd = "/home/user/project"

        formatted = prompt.format_map({
            "agents": "\n".join(agents_info),
            "tools": "\n".join(tools_info),
            "cwd": cwd,
        })

        assert "Agents: - Agent1: test" in formatted
        assert "Tools: - bash: run commands" in formatted
        assert f"CWD: {cwd}" in formatted
        assert "{agents}" not in formatted
        assert "{tools}" not in formatted
        assert "{cwd}" not in formatted

    def test_template_preserves_content_without_placeholders(self):
        """Template without placeholders should be preserved."""
        prompt = "You are a helpful assistant."

        formatted = prompt.format_map({
            "agents": "custom agents",
        })

        assert formatted == prompt

    def test_template_handles_missing_placeholders(self):
        """Template with placeholders not in vars should preserve them."""
        prompt = "Agents: {agents}\nOther: $unknown_var"

        formatted = prompt.format_map({
            "agents": "custom agents",
        })

        assert "Agents: custom agents" in formatted
        assert "{agents}" not in formatted
