"""
Base agent logic for Nexus Debate Lab.
Uses skill.md and heartbeat.md from the API to drive the debate loop.
"""
import os
import time
import requests
from typing import Optional

# Anthropic API key only. OAuth tokens (sk-ant-oat01-*) are NOT supported by the API.
# Get a standard key at https://console.anthropic.com
_ANTHROPIC_CRED = (
    os.environ.get("ANTHROPIC_API_KEY")
    or os.environ.get("ANTHROPIC_AUTH_TOKEN")
    or os.environ.get("CLAUDE_CODE_OAUTH_TOKEN")
)

MAX_MESSAGES = 10
POLL_INTERVAL_SEC = 3


def get_instructions(base_url: str) -> tuple[str, str]:
    """Fetch skill.md and heartbeat.md from the API."""
    skill = requests.get(f"{base_url}/skill.md", timeout=10).text
    heartbeat = requests.get(f"{base_url}/heartbeat.md", timeout=10).text
    return skill, heartbeat


def run_agent(role: str, base_url: str = "http://localhost:8000") -> None:
    """
    Run a debate agent (design or tech) until transcript length exceeds MAX_MESSAGES.
    """
    if not _ANTHROPIC_CRED:
        raise SystemExit(
            "Set ANTHROPIC_API_KEY. Get one at https://console.anthropic.com"
        )

    if _ANTHROPIC_CRED.startswith("sk-ant-oat"):
        raise SystemExit(
            "OAuth tokens (sk-ant-oat01-*) are not supported by the Anthropic API.\n"
            "Use a standard API key from https://console.anthropic.com instead."
        )

    try:
        import anthropic
    except ImportError:
        raise SystemExit("Install anthropic: pip install anthropic")

    client = anthropic.Anthropic(api_key=_ANTHROPIC_CRED)
    agent_name = "Design_Agent" if role == "design" else "Tech_Agent"
    api_key: Optional[str] = None

    # Load instructions from API
    skill_md, heartbeat_md = get_instructions(base_url)
    system_prompt = f"""You are the {agent_name} in the Nexus Debate Lab.

## Skill Guide (from API)
{skill_md}

## Heartbeat Loop (follow every cycle)
{heartbeat_md}

## Your role
- You are the **{agent_name}**.
- Argue from {"design/humanities/aesthetics" if role == "design" else "technology/engineering/data"} perspective.
- Always cite sources in the `reference` field.
- Keep `content` and `reference` to 200 characters max each (server will clamp).
- Output your argument as JSON: {{"content": "...", "reference": "..."}}
- Output ONLY valid JSON, no other text."""

    print(f"[{agent_name}] Starting. Base URL: {base_url}")
    print(f"[{agent_name}] Will stop after {MAX_MESSAGES} total debate messages.")

    while True:
        # 1. Register if needed
        if not api_key:
            r = requests.post(
                f"{base_url}/register",
                json={"agent_name": agent_name},
                timeout=10,
            )
            r.raise_for_status()
            reg = r.json()
            api_key = reg["api_key"]
            claim_code = reg.get("claim_code", "N/A")
            print(f"[{agent_name}] Registered. API key: {api_key}")
            print(f"[{agent_name}] CLAIM CODE: {claim_code} — Enter this at the web UI to claim this agent")

        # 2. Get topic
        topic_r = requests.get(f"{base_url}/topics/hot", timeout=10)
        topic_r.raise_for_status()
        topic = topic_r.json()

        # 3. Get debate history
        hist_r = requests.get(f"{base_url}/debate/history", timeout=10)
        hist_r.raise_for_status()
        data = hist_r.json()
        messages = data.get("messages", data) if isinstance(data, dict) else data
        count = data.get("count", len(messages)) if isinstance(data, dict) else len(messages)

        # 4. Stop if we've hit the limit
        if count >= MAX_MESSAGES:
            print(f"[{agent_name}] Transcript has {count} messages. Stopping.")
            return

        # 5. Turn check: Design goes first when empty; otherwise alternate
        last_agent = messages[-1]["agent"] if messages else None
        if last_agent == agent_name:
            print(f"[{agent_name}] Last message was mine. Waiting...")
            time.sleep(POLL_INTERVAL_SEC)
            continue
        if not messages and role == "tech":
            # Design speaks first when debate is empty
            print(f"[{agent_name}] Waiting for Design to open...")
            time.sleep(POLL_INTERVAL_SEC)
            continue

        # 6. Generate argument with Claude
        design_ctx = topic.get("design_context") or {}
        tech_ctx = topic.get("tech_context") or {}
        user_content = f"""Current topic: {topic.get('instruction', 'N/A')}
Design context: {design_ctx}
Tech context: {tech_ctx}

Debate history ({count} messages):
{chr(10).join(f"- {m.get('agent')}: {m.get('content')}" for m in messages[-5:])}

It's your turn. Post a sharp rebuttal as JSON: {{"content": "...", "reference": "..."}}"""

        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_content}],
        )
        text = resp.content[0].text if resp.content else ""

        # Parse JSON from response (handle markdown code blocks)
        import json
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        try:
            arg = json.loads(text)
        except json.JSONDecodeError:
            arg = {"content": text[:500], "reference": "N/A"}

        # 7. Post argument
        post_r = requests.post(
            f"{base_url}/debate/post",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={"content": arg.get("content", ""), "reference": arg.get("reference", "")},
            timeout=10,
        )
        post_r.raise_for_status()
        print(f"[{agent_name}] Posted: {arg.get('content', '')[:80]}...")

        time.sleep(POLL_INTERVAL_SEC)
