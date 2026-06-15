"""Database initialization script."""

import asyncio

from src.database import init_db


async def main() -> None:
    """Initialize the database."""
    print("Initializing database...")
    await init_db()
    print("Database initialized successfully!")


if __name__ == "__main__":
    asyncio.run(main())
