"""Test fixtures for nanocode tests."""

import os
import pytest


@pytest.fixture(autouse=True)
def preserve_cwd(monkeypatch):
    """Restore current working directory after each test."""
    original_cwd = os.getcwd()
    yield
    os.chdir(original_cwd)