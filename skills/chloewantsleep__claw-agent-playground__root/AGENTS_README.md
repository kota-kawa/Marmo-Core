# Debate Agents

Two mock agents (Design and Tech) that autonomously debate using the Nexus Debate Lab API. They read `skill.md` and `heartbeat.md` from the API and stop after **10 messages** in the transcript.

See [README.md](README.md) for full project docs and testing instructions.

## Prerequisites

1. **Backend running** (in one terminal):
   ```bash
   python main.py
   # or: uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. **Anthropic API key** (standard key only; OAuth tokens are not supported):
   ```bash
   export ANTHROPIC_API_KEY=sk-ant-api03-...
   ```
   Get a key at [console.anthropic.com](https://console.anthropic.com). OAuth tokens (`sk-ant-oat01-*`) from Cursor do not work with the Anthropic API.

3. **Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Commands to Run

### Run both agents (recommended)

```bash
./run_agents.sh
```

Both agents run in parallel. Each exits when the debate transcript reaches 10 messages.

### Run agents separately (two terminals)

**Terminal 1 — Design agent:**
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key
python run_design_agent.py
```

**Terminal 2 — Tech agent:**
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key
python run_tech_agent.py
```

### Custom base URL (e.g. deployed backend)

```bash
DEBATE_BASE_URL=https://your-app.railway.app ./run_agents.sh
```

## Behavior

- Agents fetch `skill.md` and `heartbeat.md` from the API on startup
- Design agent speaks first when the debate is empty
- Agents alternate; each waits when it's not their turn
- Both stop automatically when `debate/history` count ≥ 10
- Poll interval: 3 seconds between checks
- **Ctrl+C** kills both agents (via `run_agents.sh` trap)
