#!/usr/bin/env python3
"""Run a debate agent. Stops automatically after 10 debate messages.

Usage:
  python run_agent.py design
  python run_agent.py tech
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agents.agent_base import run_agent

BASE_URL = os.environ.get("DEBATE_BASE_URL", "http://localhost:8000")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in ("design", "tech"):
        print("Usage: python run_agent.py <design|tech>")
        sys.exit(1)
    run_agent(sys.argv[1], base_url=BASE_URL)
