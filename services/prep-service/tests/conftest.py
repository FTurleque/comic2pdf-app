import os
import sys

# Ensure workers disabled early so module imports during test collection don't start background threads
os.environ.setdefault("DISABLE_WORKERS", "1")

# Permettre l'import du package app depuis le dossier service
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


@pytest.fixture(autouse=True)
def test_env(tmp_path, monkeypatch):
    """Fixture autouse pour isoler DATA_DIR et désactiver les workers en tests."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DISABLE_WORKERS", "1")
    # return tmp_path for tests qui veulent écrire dedans
    return tmp_path
