"""Runtime environment configuration helpers."""

from __future__ import annotations

import os

from dotenv import find_dotenv, load_dotenv


def load_local_dotenv() -> None:
    """Load the nearest ``.env`` from the working directory without overrides."""
    dotenv_path = find_dotenv(usecwd=True)
    if dotenv_path:
        load_dotenv(dotenv_path=dotenv_path, override=False)


def required_environment(variable: str) -> str:
    """Return a required setting after loading ``.env``.

    Values already present in the process environment keep precedence over
    the local file, matching ``load_local_dotenv``'s existing behavior.
    """
    value = optional_environment(variable)
    if not value:
        raise ValueError(f"{variable} must be set in .env or the process environment")
    return value


def optional_environment(variable: str) -> str | None:
    """Return a non-empty optional setting after loading ``.env``."""
    load_local_dotenv()
    value = os.environ.get(variable, "").strip()
    return value or None


def required_positive_int_environment(variable: str) -> int:
    """Return a required positive integer setting after loading ``.env``."""
    raw_value = required_environment(variable)
    try:
        value = int(raw_value)
    except ValueError as error:
        raise ValueError(f"{variable} must be a positive integer") from error
    if value <= 0:
        raise ValueError(f"{variable} must be a positive integer")
    return value
