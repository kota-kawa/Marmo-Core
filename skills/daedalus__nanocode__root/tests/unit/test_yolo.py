"""Tests for YOLO mode."""


from nanocode.core import AutonomousAgent


class TestYoloMode:
    """Test YOLO mode functionality."""

    def test_autonomous_agent_accepts_yolo_param(self):
        """Test AutonomousAgent accepts yolo parameter."""
        agent = AutonomousAgent(yolo=True)

        assert agent.yolo is True

    def test_autonomous_agent_yolo_default_false(self):
        """Test YOLO defaults to False."""
        agent = AutonomousAgent()

        assert agent.yolo is False


class TestYoloArg:
    """Test YOLO command line argument."""

    def test_parse_yolo_flag(self):
        """Test --yolo flag is parsed."""
        import argparse


        parser = argparse.ArgumentParser()
        parser.add_argument("-y", "--yolo", action="store_true")

        args = parser.parse_args(["--yolo"])
        assert args.yolo is True

    def test_parse_yolo_short_flag(self):
        """Test -y flag is parsed."""
        import argparse


        parser = argparse.ArgumentParser()
        parser.add_argument("-y", "--yolo", action="store_true")

        args = parser.parse_args(["-y"])
        assert args.yolo is True

    def test_yolo_default_false(self):
        """Test YOLO defaults to False."""
        import argparse

        parser = argparse.ArgumentParser()
        parser.add_argument("-y", "--yolo", action="store_true")

        args = parser.parse_args([])
        assert args.yolo is False
