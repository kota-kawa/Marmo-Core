from functools import lru_cache
import re

from pydantic_settings import BaseSettings
from pydantic import field_validator


# Wallet address regex: 0x + 40 hex chars
WALLET_ADDRESS_REGEX = re.compile(r"^0x[0-9a-fA-F]{40}$")

# Transaction hash regex: 0x + 64 hex chars
TX_HASH_REGEX = re.compile(r"^0x[0-9a-fA-F]{64}$")


def validate_wallet_address(address: str) -> bool:
    """Validate Ethereum wallet address format."""
    return bool(WALLET_ADDRESS_REGEX.match(address))


def validate_tx_hash(tx_hash: str) -> bool:
    """Validate Ethereum transaction hash format."""
    return bool(TX_HASH_REGEX.match(tx_hash))


class Settings(BaseSettings):
    DATABASE_URL: str  # Required — no insecure default
    MONAD_RPC_URL: str = "https://testnet-rpc.monad.xyz"
    X402_API_KEY: str = ""
    X402_API_URL: str = "https://api.x402.dev"
    SAFE_API_URL: str = "https://safe-client.safe.global"
    ENCRYPTION_KEY: str = ""  # Optional for dev
    ADMIN_KEY: str  # Required — no hardcoded default
    WEBHOOK_SECRET: str = ""  # Optional but recommended for production
    TURSO_DATABASE_URL: str = ""
    TURSO_AUTH_TOKEN: str = ""
    AGENT_API_KEY: str  # Required for secure agent access
    FRONTEND_URL: str = ""  # Production frontend origin (CORS)
    DEBUG: bool = False  # Debug mode flag

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("DATABASE_URL must be set explicitly")
        return v

    @field_validator("ADMIN_KEY")
    @classmethod
    def validate_admin_key(cls, v: str) -> str:
        if not v or v.strip() == "" or v == "genesis-admin-key":
            raise ValueError("ADMIN_KEY must be set to a secure value (not the default)")
        return v

    @field_validator("AGENT_API_KEY")
    @classmethod
    def validate_agent_key(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("AGENT_API_KEY must be set to allow agent connections")
        if len(v) < 32:
            raise ValueError("AGENT_API_KEY must be at least 32 characters long for security")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
