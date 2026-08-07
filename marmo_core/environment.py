"""Runtime environment configuration helpers."""

from __future__ import annotations

from dotenv import find_dotenv, load_dotenv


def load_local_dotenv() -> None:
    """Load the nearest ``.env`` from the working directory without overrides."""
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path, override=False)
