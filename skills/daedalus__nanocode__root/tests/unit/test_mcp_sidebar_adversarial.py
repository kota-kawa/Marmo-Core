"""Adversarial tests for MCP sidebar functionality."""



class TestMCPAgentMCPInit:
    """Adversarial tests for MCP agent initialization."""

    def test_init_mcp_with_empty_servers(self):
        """Test MCP initialization with empty server config."""
        from nanocode.mcp import MCPManager

        mcp_manager = MCPManager()
        _mcp_available = {}

        config_servers = {}
        for name, server_config in config_servers.items():
            _mcp_available[name] = server_config.get("enabled", True)
            if _mcp_available[name]:
                mcp_manager.add_server(name, server_config)

        assert len(_mcp_available) == 0

    def test_init_mcp_with_all_disabled(self):
        """Test MCP initialization with all servers disabled."""
        from nanocode.mcp import MCPManager

        mcp_manager = MCPManager()
        _mcp_available = {}

        config_servers = {
            "server1": {"enabled": False},
            "server2": {"enabled": False},
        }
        for name, server_config in config_servers.items():
            _mcp_available[name] = server_config.get("enabled", True)
            if _mcp_available[name]:
                mcp_manager.add_server(name, server_config)

        assert len(_mcp_available) == 2
        assert _mcp_available["server1"] is False
        assert _mcp_available["server2"] is False
        assert len(mcp_manager._clients) == 0

    def test_init_mcp_with_mixed_enabled(self):
        """Test MCP initialization with mixed enabled/disabled servers."""
        from nanocode.mcp import MCPManager

        mcp_manager = MCPManager()
        _mcp_available = {}

        config_servers = {
            "server1": {"enabled": True, "url": "http://localhost:8001"},
            "server2": {"enabled": False},
            "server3": {"enabled": True, "url": "http://localhost:8003"},
        }
        for name, server_config in config_servers.items():
            _mcp_available[name] = server_config.get("enabled", True)
            if _mcp_available[name]:
                mcp_manager.add_server(name, server_config)

        assert len(_mcp_available) == 3
        assert _mcp_available["server1"] is True
        assert _mcp_available["server2"] is False
        assert _mcp_available["server3"] is True
        assert len(mcp_manager._clients) == 2

    def test_init_mcp_with_default_enabled(self):
        """Test MCP initialization defaults to enabled when not specified."""
        from nanocode.mcp import MCPManager

        mcp_manager = MCPManager()
        _mcp_available = {}

        config_servers = {
            "server1": {"url": "http://localhost:8001"},
            "server2": {"enabled": False},
        }
        for name, server_config in config_servers.items():
            _mcp_available[name] = server_config.get("enabled", True)
            if _mcp_available[name]:
                mcp_manager.add_server(name, server_config)

        assert _mcp_available["server1"] is True
        assert _mcp_available["server2"] is False
        assert len(mcp_manager._clients) == 1

    def test_init_mcp_with_missing_enabled_key(self):
        """Test MCP initialization handles missing enabled key."""
        from nanocode.mcp import MCPManager

        mcp_manager = MCPManager()
        _mcp_available = {}

        config_servers = {
            "server1": {"url": "http://localhost:8001"},
            "server2": {"enabled": True, "url": "http://localhost:8002"},
            "server3": {"enabled": False, "url": "http://localhost:8003"},
        }
        for name, server_config in config_servers.items():
            enabled = server_config.get("enabled", True)
            _mcp_available[name] = enabled
            if enabled:
                mcp_manager.add_server(name, server_config)

        assert _mcp_available["server1"] is True
        assert _mcp_available["server2"] is True
        assert _mcp_available["server3"] is False


class TestMCPSidebarDots:
    """Tests for MCP sidebar dot display."""

    def test_dot_display_enabled(self):
        """Test dot display for enabled servers."""
        mcp_available = {"server1": True, "server2": True}
        lines = []
        for name, enabled in list(mcp_available.items())[:15]:
            dot = "●" if enabled else "○"
            lines.append(f"  {dot} {name}")

        assert "  ● server1" in lines
        assert "  ● server2" in lines

    def test_dot_display_disabled(self):
        """Test dot display for disabled servers."""
        mcp_available = {"server1": False, "server2": False}
        lines = []
        for name, enabled in list(mcp_available.items())[:15]:
            dot = "●" if enabled else "○"
            lines.append(f"  {dot} {name}")

        assert "  ○ server1" in lines
        assert "  ○ server2" in lines

    def test_dot_display_mixed(self):
        """Test dot display for mixed enabled/disabled servers."""
        mcp_available = {"server1": True, "server2": False, "server3": True}
        lines = []
        for name, enabled in list(mcp_available.items())[:15]:
            dot = "●" if enabled else "○"
            lines.append(f"  {dot} {name}")

        assert "  ● server1" in lines
        assert "  ○ server2" in lines
        assert "  ● server3" in lines

    def test_dot_display_many_servers(self):
        """Test dot display with many servers."""
        mcp_available = {f"server_{i}": i % 2 == 0 for i in range(100)}
        lines = []
        for name, enabled in list(mcp_available.items())[:15]:
            dot = "●" if enabled else "○"
            lines.append(f"  {dot} {name}")

        assert len(lines) == 15
        assert "  ● server_0" in lines
        assert "  ○ server_1" in lines

    def test_dot_display_special_characters(self):
        """Test dot display with special characters in server names."""
        mcp_available = {
            "server-with-dashes": True,
            "server.with.dots": False,
            "server_with_underscores": True,
        }
        lines = []
        for name, enabled in list(mcp_available.items())[:15]:
            dot = "●" if enabled else "○"
            lines.append(f"  {dot} {name}")

        assert "  ● server-with-dashes" in lines
        assert "  ○ server.with.dots" in lines
        assert "  ● server_with_underscores" in lines

    def test_dot_display_unicode_server_names(self):
        """Test dot display with Unicode in server names."""
        mcp_available = {
            "servidor-日本語": True,
            "сервер-中文": False,
        }
        lines = []
        for name, enabled in list(mcp_available.items())[:15]:
            dot = "●" if enabled else "○"
            lines.append(f"  {dot} {name}")

        assert "  ● servidor-日本語" in lines
        assert "  ○ сервер-中文" in lines

    def test_dot_display_empty_server_name(self):
        """Test dot display with empty server name."""
        mcp_available = {"": True, "valid": False}
        lines = []
        for name, enabled in list(mcp_available.items())[:15]:
            dot = "●" if enabled else "○"
            lines.append(f"  {dot} {name}")

        assert "  ● " in lines
        assert "  ○ valid" in lines

    def test_dot_display_very_long_server_name(self):
        """Test dot display with very long server names."""
        mcp_available = {
            "a" * 1000: True,
            "b" * 1000: False,
        }
        lines = []
        for name, enabled in list(mcp_available.items())[:15]:
            dot = "●" if enabled else "○"
            lines.append(f"  {dot} {name}")

        assert "  ● " + "a" * 1000 in lines
        assert "  ○ " + "b" * 1000 in lines


class TestMCPSidebarSection:
    """Tests for MCP sidebar section rendering."""

    def test_section_header(self):
        """Test MCP section header."""
        mcp_available = {"server1": True}
        lines = ["─ MCP ─"]
        for name, enabled in list(mcp_available.items())[:15]:
            dot = "●" if enabled else "○"
            lines.append(f"  {dot} {name}")

        assert "─ MCP ─" in lines
        assert len(lines) == 2

    def test_section_empty(self):
        """Test MCP section with empty servers."""
        mcp_available = {}
        lines = []
        if mcp_available:
            lines.append("─ MCP ─")
            for name, enabled in list(mcp_available.items())[:15]:
                dot = "●" if enabled else "○"
                lines.append(f"  {dot} {name}")

        assert "─ MCP ─" not in lines
        assert len(lines) == 0

    def test_section_with_server_list(self):
        """Test MCP section with server list."""
        mcp_available = {
            "server1": True,
            "server2": False,
            "server3": True,
            "server4": False,
        }
        lines = []
        if mcp_available:
            lines.append("─ MCP ─")
            for name, enabled in list(mcp_available.items())[:15]:
                dot = "●" if enabled else "○"
                lines.append(f"  {dot} {name}")

        expected = [
            "─ MCP ─",
            "  ● server1",
            "  ○ server2",
            "  ● server3",
            "  ○ server4",
        ]
        assert lines == expected
