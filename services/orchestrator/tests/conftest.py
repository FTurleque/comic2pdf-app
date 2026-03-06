"""
Conftest orchestrator — isolation xdist et markers.

- Isole DATA_DIR via tmp_path (autouse) → chaque worker xdist a son propre dossier.
- Marque automatiquement les classes qui démarrent un vrai serveur HTTP comme ``serial``
  (test_http_server, test_auth) pour les exécuter séquentiellement sans conflit de port.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


def pytest_collection_modifyitems(items):
    """Marque automatiquement serial les tests des modules serveur HTTP."""
    serial_modules = {"test_http_server", "test_auth"}
    for item in items:
        module_name = item.module.__name__.split(".")[-1]
        if module_name in serial_modules:
            item.add_marker(pytest.mark.serial)


@pytest.fixture(autouse=True)
def isolate_data_dir(tmp_path, monkeypatch):
    """Fixture autouse : isole DATA_DIR et désactive les workers en tests."""
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("DISABLE_WORKERS", "1")
    return tmp_path

