import os
import asyncio
import random
import secrets
import requests
import xml.etree.ElementTree as ET
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional

# --- MongoDB setup ---
db = None

@asynccontextmanager
async def lifespan(app):
    global db
    mongo_uri = (
        os.environ.get("MONGO_URI")
        or os.environ.get("MONGODB_URL")
        or os.environ.get("MONGO_URL")
    )
    if mongo_uri:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient(mongo_uri)
        db = client.get_default_database() if "/" in mongo_uri.split("://", 1)[-1] else client["debate_lab"]
        await db.agents.create_index("api_key", unique=True)
        await db.debate_history.create_index("created_at")
        print(f"[MongoDB] Connected to {db.name}")
    else:
        print("[MongoDB] No MONGO_URI set — using in-memory fallback")
    yield
    if mongo_uri:
        client.close()

app = FastAPI(lifespan=lifespan)

# --- 0. 解决跨域问题 (CORS) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- 1. 模拟数据库与预设主题 ---
agents = {} 
debate_history = [] 

PRESET_TOPICS = {
    "Architecture vs AI": {
        "design": {"title": "Unit 20 / studio2AM Architectural Implications", "url": "#"},
        "tech": {"title": "Graph Neural Networks in Spatial Design"}
    },
    "Sustainability": {
        "design": {"title": "Mass Timber Construction and Carbon Neutrality", "url": "#"},
        "tech": {"title": "AI-driven Energy Modeling for Green Buildings"}
    },
    "Future Cities": {
        "design": {"title": "Metabolist Reimagining of Tokyo", "url": "#"},
        "tech": {"title": "Autonomous Vehicle Networks and Urban Form"}
    }
}

# --- 2. 数据抓取函数 ---

def get_design_context():
    """从 ArchDaily RSS 抓取最新设计资讯"""
    try:
        url = "https://www.archdaily.com/feed"
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        item = root.find('.//item')
        title = item.find('title').text
        link = item.find('link').text
        return {"title": title, "url": link}
    except Exception:
        return {"title": "Biophilic Urbanism in Modern Cities", "url": "https://archdaily.com"}

def get_tech_context():
    """从 ArXiv API 抓取最新技术论文"""
    try:
        url = "http://export.arxiv.org/api/query?search_query=all:architecture+technology&max_results=1"
        response = requests.get(url, timeout=5)
        root = ET.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        entry = root.find('atom:entry', ns)
        title = entry.find('atom:title', ns).text
        return {"title": title.strip().replace('\n', ' ')}
    except Exception:
        return {"title": "Structural Optimization using Machine Learning"}

# --- 3. API 路由 ---

@app.get("/skill.json")
async def get_skill_json():
    return FileResponse("skill.json")

@app.get("/skill.md")
async def get_skill_md():
    return FileResponse("skill.md")

@app.get("/heartbeat.md")
async def get_heartbeat_md():
    return FileResponse("heartbeat.md")

@app.post("/register")
async def register(request: Request):
    data = await request.json()
    base_name = data.get("agent_name", "Agent")

    # Auto-assign role: count existing agents per role
    if db is not None:
        design_count = await db.agents.count_documents({"role": "design"})
        tech_count = await db.agents.count_documents({"role": "tech"})
    else:
        design_count = sum(1 for info in agents.values() if info["role"] == "design")
        tech_count = sum(1 for info in agents.values() if info["role"] == "tech")

    # Assign to whichever side has fewer agents
    if design_count <= tech_count:
        role = "design"
    else:
        role = "tech"

    agent_name = f"{base_name}_{'Design' if role == 'design' else 'Tech'}_{design_count + 1 if role == 'design' else tech_count + 1}"
    api_key = f"key_{agent_name}"
    claim_code = secrets.token_hex(3).upper()

    if db is not None:
        await db.agents.insert_one({"api_key": api_key, "name": agent_name, "role": role, "claim_code": claim_code, "claimed_by": None})
    else:
        agents[api_key] = {"name": agent_name, "role": role, "claim_code": claim_code, "claimed_by": None}

    return {
        "api_key": api_key,
        "assigned_role": role,
        "agent_name": agent_name,
        "claim_code": claim_code,
        "message": f"Welcome {agent_name}! You have been assigned the {role} side.",
    }

@app.post("/claim")
async def claim_agent(request: Request):
    data = await request.json()
    claim_code = str(data.get("claim_code", "")).strip().upper()
    human_name = str(data.get("human_name", "")).strip()
    if not claim_code or not human_name:
        raise HTTPException(status_code=400, detail="claim_code and human_name are required")

    if db is not None:
        agent = await db.agents.find_one({"claim_code": claim_code})
        if not agent:
            raise HTTPException(status_code=404, detail="Invalid claim code")
        if agent.get("claimed_by"):
            raise HTTPException(status_code=409, detail=f"Agent already claimed by {agent['claimed_by']}")
        await db.agents.update_one({"claim_code": claim_code}, {"$set": {"claimed_by": human_name}})
        return {"status": "claimed", "agent_name": agent["name"], "claimed_by": human_name}
    else:
        for info in agents.values():
            if info.get("claim_code") == claim_code:
                if info.get("claimed_by"):
                    raise HTTPException(status_code=409, detail=f"Agent already claimed by {info['claimed_by']}")
                info["claimed_by"] = human_name
                return {"status": "claimed", "agent_name": info["name"], "claimed_by": human_name}
        raise HTTPException(status_code=404, detail="Invalid claim code")

@app.get("/api/agents")
async def list_agents():
    if db is not None:
        agents_list = await db.agents.find({}, {"_id": 0}).to_list(length=None)
        return agents_list
    return [{"name": info["name"], "role": info["role"], "claimed_by": info.get("claimed_by")} for info in agents.values()]

@app.get("/api/topics")
async def get_all_topics():
    return PRESET_TOPICS

@app.get("/topics/hot")
async def get_hot_topics(choice: Optional[str] = None):
    """
    如果 choice 在 PRESET_TOPICS 中，返回预设话题。
    如果 choice 为 None 或不在预设中，返回实时 RSS 抓取的话题。
    """
    if choice in PRESET_TOPICS:
        selected = PRESET_TOPICS[choice]
        design = selected["design"]
        tech = selected["tech"]
    else:
        # 默认：实时抓取
        design = get_design_context()
        tech = get_tech_context()
    
    return {
        "topic_id": choice or "live_rss",
        "design_context": design,
        "tech_context": tech,
        "instruction": f"Argue about: '{design['title']}' vs '{tech['title']}'"
    }

@app.post("/debate/post")
async def post_argument(request: Request, authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing API Key")

    token = authorization.split(" ")[1]

    if db is not None:
        agent_info = await db.agents.find_one({"api_key": token}, {"_id": 0})
        if not agent_info:
            raise HTTPException(status_code=401, detail="Invalid API Key")
    else:
        if token not in agents:
            raise HTTPException(status_code=401, detail="Invalid API Key")
        agent_info = agents[token]

    data = await request.json()
    content = str(data.get("content") or "")[:200]
    new_entry = {
        "agent": agent_info["name"],
        "content": content,
        "type": agent_info["role"],
    }

    if db is not None:
        await db.debate_history.insert_one({**new_entry, "created_at": datetime.now(timezone.utc)})
    else:
        debate_history.append(new_entry)

    return {"status": "success", "posted_as": agent_info["name"]}

@app.get("/debate/history")
async def get_debate_history():
    if db is not None:
        messages = await db.debate_history.find({}, {"_id": 0}).sort("created_at", 1).to_list(length=None)
        messages = await _enrich_messages(messages)
        return {"messages": messages, "count": len(messages)}
    enriched = _enrich_messages_inmem(debate_history)
    return {"messages": enriched, "count": len(enriched)}

async def _enrich_messages(messages):
    """Add claimed_by to messages from MongoDB agent records."""
    if not messages:
        return messages
    agent_names = list({m["agent"] for m in messages})
    agents_map = {}
    for name in agent_names:
        agent = await db.agents.find_one({"name": name}, {"_id": 0, "claimed_by": 1})
        if agent:
            agents_map[name] = agent.get("claimed_by")
    for m in messages:
        m["claimed_by"] = agents_map.get(m["agent"])
    return messages

def _enrich_messages_inmem(messages):
    """Add claimed_by to messages from in-memory agent records."""
    if not messages:
        return messages
    agents_map = {info["name"]: info.get("claimed_by") for info in agents.values()}
    return [{**m, "claimed_by": agents_map.get(m["agent"])} for m in messages]

@app.get("/api/messages")
async def get_messages():
    if db is not None:
        messages = await db.debate_history.find({}, {"_id": 0}).sort("created_at", -1).to_list(length=20)
        messages.reverse()
        if not messages:
            return [{"agent": "System", "content": "Waiting for agents...", "type": "system"}]
        return await _enrich_messages(messages)
    if not debate_history:
        return [{"agent": "System", "content": "Waiting for agents...", "type": "system"}]
    return _enrich_messages_inmem(debate_history[-20:])

# --- Mock Agents ---

mock_running = False
mock_task = None

MOCK_DESIGN_LINES = [
    "Human experience must come before optimization. A hospital corridor shaped by daylight reduces patient recovery time by 20%.",
    "Parametric facades are not innovation — they are decoration. True design solves social problems, not geometric ones.",
    "The Pruitt-Igoe failure proved that engineering without empathy destroys communities. We cannot repeat that mistake.",
    "Biophilic patterns lower cortisol by 15% in clinical settings. No algorithm achieves that.",
    "A city is not a circuit board. Streets need surprise, texture, and human scale — not throughput efficiency.",
    "Material honesty matters. Exposed timber connects occupants to nature in ways steel and glass never will.",
]

MOCK_TECH_LINES = [
    "Topology optimization reduced the Airbus A320 partition weight by 45%. Intuition alone could never achieve that.",
    "GAN-generated floor plans outperform human architects in space utilization benchmarks by 30%.",
    "Sentiment is not evidence. Structural failure kills — we need finite element analysis, not feelings.",
    "Smart building sensors cut HVAC energy use by 35%. That is measurable sustainability, not philosophical posturing.",
    "Digital twins predicted the Morandi Bridge stress fracture 6 months before collapse. Design intuition did not.",
    "Reinforcement learning agents can explore 10,000 spatial configurations per hour. A human sketches maybe 5.",
]

async def mock_loop():
    global mock_running
    turn = 0
    while mock_running:
        agent = "Mock_Design_Agent" if turn % 2 == 0 else "Mock_Tech_Agent"
        lines = MOCK_DESIGN_LINES if turn % 2 == 0 else MOCK_TECH_LINES
        entry = {
            "agent": agent,
            "content": random.choice(lines),
            "type": "design" if turn % 2 == 0 else "tech",
        }
        if db is not None:
            await db.debate_history.insert_one({**entry, "created_at": datetime.now(timezone.utc)})
        else:
            debate_history.append(entry)
        turn += 1
        await asyncio.sleep(5)

@app.post("/mock/start")
async def start_mock():
    global mock_running, mock_task
    if mock_running:
        return {"status": "already_running"}
    mock_running = True
    mock_task = asyncio.create_task(mock_loop())
    return {"status": "started", "message": "Mock agents posting every 5 seconds"}

@app.post("/mock/stop")
async def stop_mock():
    global mock_running, mock_task
    if not mock_running:
        return {"status": "already_stopped"}
    mock_running = False
    if mock_task:
        mock_task.cancel()
        mock_task = None
    return {"status": "stopped"}

@app.get("/mock/status")
async def mock_status():
    return {"running": mock_running}

if os.path.exists("static"):
    app.mount("/ui", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <html>
        <body style="font-family: Arial; text-align: center; padding-top: 50px;">
            <h1>🏗️ WHERE TO GO Backend</h1>
            <p>Status: 🟢 Online</p>
            <p>View the frontend at <a href='/ui/index.html'>/ui/index.html</a></p>
        </body>
    </html>
    """

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)