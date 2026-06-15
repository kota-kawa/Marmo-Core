"""Tests for main.py CLI arguments."""

from unittest.mock import patch

import pytest


class TestParseArgs:
    """Test argument parsing."""

    def test_proxy_argument(self):
        """Test --proxy argument is parsed correctly."""
        import sys

        from nanocode.main import parse_args

        with patch.object(sys, "argv", ["main.py", "--proxy", "http://localhost:8080"]):
            args = parse_args()
            assert args.proxy == "http://localhost:8080"

    def test_proxy_argument_none(self):
        """Test --proxy defaults to None when not provided."""
        import sys

        from nanocode.main import parse_args

        with patch.object(sys, "argv", ["main.py"]):
            args = parse_args()
            assert args.proxy is None


class TestRichConsole:
    """Test Rich console import in main.py."""

    def test_console_import(self):
        """Test console can be imported from main."""
        from rich.console import Console

        c = Console()
        assert c is not None

    def test_console_print(self):
        """Test console.print works."""
        from rich.console import Console

        c = Console()
        c.print("[yellow]test[/yellow]")


class TestFormatMarkdown:
    """Test _format_markdown function."""

    def test_format_markdown_simple(self):
        """Test _format_markdown formats bold text."""
        from nanocode.main import _format_markdown

        result = _format_markdown("Hello **world**")
        assert "[magenta bold]world[/magenta bold]" in result

    def test_format_markdown_no_bold(self):
        """Test _format_markdown passes text without bold."""
        from nanocode.main import _format_markdown

        result = _format_markdown("Hello world")
        assert "world" in result
        assert "[magenta" not in result

    def test_format_markdown_multiple_bold(self):
        """Test _format_markdown handles multiple bold sections."""
        from nanocode.main import _format_markdown

        result = _format_markdown("**one** and **two**")
        assert result.count("[magenta bold]") == 2

    def test_no_proxy_argument(self):
        """Test --no-proxy argument is parsed correctly."""
        import sys

        from nanocode.main import parse_args

        with patch.object(sys, "argv", ["main.py", "--no-proxy"]):
            args = parse_args()
            assert args.no_proxy is True


if __name__ == "__main__":
    pytest.main([__file__])
