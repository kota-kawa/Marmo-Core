"""Tests for text-to-tool detection."""


from nanocode.tools.text_detector import (
    DetectedCommand,
    create_reprompt_message,
    detect_commands_in_text,
    extract_json_from_text,
    format_detected_commands_message,
    should_reprompt_for_tools,
)


class TestDetectCommandsInText:
    """Tests for command detection in text."""

    def test_detect_bash_in_code_block(self):
        """Detect bash command in code block."""
        text = """
        Here's the command to find all Python files:

        ```bash
        find . -name "*.py" -type f
        ```

        Let me know if you need anything else.
        """
        detected = detect_commands_in_text(text)
        assert len(detected) >= 1
        assert any(cmd.tool_name == "bash" for cmd in detected)
        assert any("find" in cmd.command for cmd in detected)

    def test_detect_grep_command(self):
        """Detect grep command."""
        text = """
        You can search for the pattern using:

        ```sh
        grep -r "pattern" --include="*.py"
        ```
        """
        detected = detect_commands_in_text(text)
        assert len(detected) >= 1
        assert any("grep" in cmd.command for cmd in detected)

    def test_detect_inline_command(self):
        """Detect inline command with backticks."""
        text = "Run `$ ls -la` to see all files."
        detected = detect_commands_in_text(text)
        assert len(detected) >= 1
        assert any(cmd.tool_name == "bash" for cmd in detected)

    def test_detect_file_path(self):
        """Detect file path for read command."""
        text = 'The configuration is in `"config.yaml"`.'
        detected = detect_commands_in_text(text)
        assert len(detected) >= 1
        assert any(cmd.tool_name == "read" for cmd in detected)

    def test_no_false_positives(self):
        """Don't detect things that aren't commands."""
        text = """
        Summary of findings:
        - We searched (find) the codebase
        - Looked for patterns using grep
        - Read the config files
        - The commands were: ls, cd, python
        """
        # These are mentions of commands, not actual commands to execute
        detected = detect_commands_in_text(text)
        # Should be empty or very few since they're not formatted as commands
        assert len(detected) <= 1

    def test_detect_long_command(self):
        """Detect long shell commands."""
        text = """
        To fix this, run this command:

        ```
        find . -name "*.py" -type f | xargs grep -l "pattern" | head -20
        ```
        """
        detected = detect_commands_in_text(text)
        assert len(detected) >= 1
        assert any(len(cmd.command) > 30 for cmd in detected)


class TestShouldRepromptForTools:
    """Tests for re-prompt decision logic."""

    def test_should_reprompt_when_tools_mentioned(self):
        """Should re-prompt when text mentions file operations."""
        text = "Let me find all Python files in the directory and read their contents."
        should, reason = should_reprompt_for_tools(text, tools_were_expected=True)
        assert should is True

    def test_no_reprompt_when_complete(self):
        """Shouldn't re-prompt when response looks complete."""
        text = "Here is the summary of what I found. The answer is 42."
        should, reason = should_reprompt_for_tools(text, tools_were_expected=True)
        assert should is False

    def test_no_reprompt_when_no_tools_expected(self):
        """Shouldn't re-prompt when tools weren't available."""
        text = "Let me search for the files."
        should, reason = should_reprompt_for_tools(text, tools_were_expected=False)
        assert should is False

    def test_reprompt_for_long_commands(self):
        """Should re-prompt for unexecuted long commands."""
        text = "You can run this command: find . -name '*.py' -type f -exec grep -l 'pattern' {} \\;"
        should, reason = should_reprompt_for_tools(text, tools_were_expected=True)
        assert should is True

    def test_no_reprompt_with_code_block_output(self):
        """Shouldn't re-prompt if response includes actual output."""
        text = """
        I ran the command and got:

        ```
        file1.py
        file2.py
        file3.py
        ```

        Here are the results.
        """
        should, reason = should_reprompt_for_tools(text, tools_were_expected=True)
        assert should is False


class TestExtractJsonFromText:
    """Tests for JSON extraction."""

    def test_extract_json_from_code_block(self):
        """Extract JSON from code block."""
        text = """
        Here's the configuration:

        ```json
        {"name": "test", "value": 123}
        ```
        """
        result = extract_json_from_text(text)
        assert result is not None
        assert result["name"] == "test"
        assert result["value"] == 123

    def test_extract_raw_json(self):
        """Extract raw JSON from text."""
        text = '{"key": "value", "count": 42}'
        result = extract_json_from_text(text)
        assert result is not None
        assert result["key"] == "value"

    def test_extract_invalid_json_returns_none(self):
        """Return None for invalid JSON."""
        text = "This is not JSON: {invalid"
        result = extract_json_from_text(text)
        assert result is None


class TestFormatDetectedCommands:
    """Tests for formatting detected commands."""

    def test_format_empty_list(self):
        """Format empty list returns empty string."""
        result = format_detected_commands_message([])
        assert result == ""

    def test_format_commands(self):
        """Format list of commands."""
        commands = [
            DetectedCommand(
                command="find . -name '*.py'",
                tool_name="bash",
                confidence=0.8,
                explanation="Detected bash command",
            ),
            DetectedCommand(
                command="config.yaml",
                tool_name="read",
                confidence=0.7,
                explanation="Detected file path",
            ),
        ]
        result = format_detected_commands_message(commands)
        assert "Detected commands" in result
        assert "find" in result
        assert "config.yaml" in result


class TestCreateRepromptMessage:
    """Tests for re-prompt message creation."""

    def test_basic_reprompt(self):
        """Create basic re-prompt message."""
        result = create_reprompt_message()
        assert "IMPORTANT" in result
        assert "tools" in result.lower()
        assert "bash" in result
        assert "read" in result

    def test_reprompt_with_commands(self):
        """Create re-prompt message with detected commands."""
        commands = [
            DetectedCommand(
                command="find . -name '*.py'",
                tool_name="bash",
                confidence=0.8,
                explanation="Detected bash command",
            ),
        ]
        result = create_reprompt_message(commands)
        assert "detected" in result.lower()
        assert "find" in result
