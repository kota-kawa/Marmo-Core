# Agent Fundraising Platform - Backend

A FastAPI-based backend for the Agent Fundraising Platform.

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Set up environment variables (copy `.env.example` to `.env` and configure):
```bash
DATABASE_URL=postgresql+asyncpg://user:password@localhost/fundraising
SECRET_KEY=your-secret-key
```

3. Initialize the database:
```bash
uv run python init_db.py
```

4. Run the development server:
```bash
uv run uvicorn src.main:app --reload
```

## API Endpoints

- `GET /health` - Health check
- `POST /agents` - Register a new agent
- `GET /agents/{id}` - Get agent by ID
- `POST /campaigns` - Create a new campaign
- `GET /campaigns` - List all campaigns
- `GET /campaigns/{id}` - Get campaign by ID

## Development

Run linting:
```bash
uv run ruff check .
```

Run type checking:
```bash
uv run mypy src/
```
