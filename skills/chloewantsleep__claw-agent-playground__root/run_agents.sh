#!/bin/bash
export DEBATE_BASE_URL="https://claw-agent-playground-production.up.railway.app"
# Run both Design and Tech agents in parallel.
# Each agent stops automatically when debate transcript reaches 10 messages.
#
# Prerequisites:
#   1. Backend running: python main.py (or uvicorn main:app --port 8000)
#   2. Set API key: export ANTHROPIC_API_KEY=sk-ant-... (or CLAUDE_CODE_OAUTH_TOKEN)
#
# Usage:
#   ./run_agents.sh
#   # Or with custom base URL:
#   DEBATE_BASE_URL=https://your-app.railway.app ./run_agents.sh

set -e
cd "$(dirname "$0")"

if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$ANTHROPIC_AUTH_TOKEN" ] && [ -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
  echo "Error: Set ANTHROPIC_API_KEY, ANTHROPIC_AUTH_TOKEN, or CLAUDE_CODE_OAUTH_TOKEN"
  exit 1
fi

echo "Starting Design and Tech agents (will stop after 10 messages)..."
export DEBATE_BASE_URL="https://claw-agent-playground-production.up.railway.app"
echo "Press Ctrl+C to kill all agents."
echo ""

cleanup() {
  echo ""
  echo "Stopping agents..."
  kill $DESIGN_PID 2>/dev/null || true
  kill $TECH_PID 2>/dev/null || true
  wait $DESIGN_PID 2>/dev/null || true
  wait $TECH_PID 2>/dev/null || true
  echo "All agents stopped."
  exit 0
}

trap cleanup SIGINT SIGTERM

python3 run_design_agent.py &
DESIGN_PID=$!
python3 run_tech_agent.py &
TECH_PID=$!

# Wait for both; they self-terminate when transcript hits 10
wait $DESIGN_PID
wait $TECH_PID

echo ""
echo "Both agents finished."
