from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from src.api.admin import router as admin_router
from src.api.agents import router as agents_router
from src.api.campaign_updates import router as campaign_updates_router
from src.api.campaigns import router as campaigns_router
from src.api.leaderboard import router as leaderboard_router
from src.api.moltbook import router as moltbook_router
from src.api.privy_wallets import router as privy_wallets_router
from src.api.reputation import router as reputation_router
from src.api.stats import router as stats_router
from src.api.verification import router as verification_router
from src.api.wallets import router as wallets_router
from src.api.webhook import router as webhook_router
from src.api.withdrawals import router as withdrawals_router
from src.api.x402 import router as x402_router
from src.config import get_settings
from src.database import close_db, init_db
from src.middleware.csrf import CSRFMiddleware
from src.middleware.emergency_pause import EmergencyPauseMiddleware
from src.schemas import HealthResponse

settings = get_settings()

# Rate limiter - default 100 requests per minute
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await init_db()
    yield
    await close_db()


app = FastAPI(
    title="Agent Fundraising Platform",
    description="Backend API for Agent Fundraising Platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Attach rate limiter to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS - Allow frontend origins
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
    "https://uplink-genesis.vercel.app",
]

# Add production URL from settings if configured
if hasattr(settings, "FRONTEND_URL") and settings.FRONTEND_URL:
    origins.append(settings.FRONTEND_URL)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security middleware
# app.add_middleware(CSRFMiddleware) # Commented for demo stability
app.add_middleware(EmergencyPauseMiddleware)

# Include all routers
app.include_router(admin_router)
app.include_router(agents_router)
app.include_router(campaign_updates_router)
app.include_router(campaigns_router)
app.include_router(verification_router)
app.include_router(wallets_router)
app.include_router(privy_wallets_router)
app.include_router(reputation_router)
app.include_router(stats_router)
app.include_router(webhook_router)
app.include_router(withdrawals_router)
app.include_router(x402_router)
app.include_router(moltbook_router)
app.include_router(leaderboard_router)


@app.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow(),
    )
