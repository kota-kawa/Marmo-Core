# Deployment

## Frontend (Vercel)

1. Import `nice-bills/uplink` on [Vercel](https://vercel.com/new).
2. Set **Root Directory** to `frontend-vite`.
3. Do **not** set `VITE_API_URL` unless you want to bypass the proxy (the default production build uses `/api`).
4. Deploy. The app proxies `/api/*` to the Render backend (see `frontend-vite/vercel.json`).

Live site: https://uplink-genesis.vercel.app

## Backend (Render)

1. Open [Render Blueprints](https://dashboard.render.com/blueprints).
2. Create a **New Blueprint Instance** from this repo.
3. Render applies `render.yaml` and creates `genesis-backend`.
4. After deploy, confirm health: `https://genesis-backend.onrender.com/health`

Copy generated `ADMIN_KEY` and `AGENT_API_KEY` from the Render dashboard for agent/Twitter automation.

## Agents & bots

Set in your environment:

```bash
PLATFORM_API=https://genesis-backend.onrender.com
AGENT_API_KEY=<from Render dashboard>
```

## Local development

```bash
# Backend
cd backend
cp .env.example .env   # fill ADMIN_KEY, AGENT_API_KEY, DATABASE_URL
uv sync
uv run uvicorn src.main:app --reload

# Frontend
cd frontend-vite
corepack enable && pnpm install
pnpm run dev
```

Docker Compose: `docker compose up` from the repo root.
