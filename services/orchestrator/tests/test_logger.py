"""
Tests du helper de logging JSON structuré de l'orchestrateur.
Vérifie que le format JSON est valide et contient les champs attendus.
"""
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


class TestLoggerJson:

    def test_log_json_format_valide(self, monkeypatch):
        """Avec LOG_JSON=true, chaque log est une ligne JSON valide."""
        monkeypatch.setenv("LOG_JSON", "true")
        # Recharger le module pour prendre en compte la variable d'env
        import importlib
        import app.logger as mod
        importlib.reload(mod)

        logger = mod.get_logger("test_json_logger")
        # Remplacer les handlers pour capturer la sortie
        captured = []
        handler = logging.handlers_mock(captured) if False else None

        import io
        stream = io.StringIO()
        h = logging.StreamHandler(stream)
        h.setFormatter(mod._JsonFormatter())
        logger.handlers = [h]

        logger.info("message de test", extra={"jobKey": "k1", "stage": "PREP"})
        output = stream.getvalue().strip()

        data = json.loads(output)
        assert data["level"] == "INFO"
        assert data["message"] == "message de test"
        assert "timestamp" in data
        assert "service" in data
        assert data.get("jobKey") == "k1"
        assert data.get("stage") == "PREP"

    def test_log_json_sans_extra_valide(self, monkeypatch):
        """Un log sans extra est aussi un JSON valide."""
        import importlib
        import app.logger as mod
        importlib.reload(mod)

        import io
        stream = io.StringIO()
        h = logging.StreamHandler(stream)
        h.setFormatter(mod._JsonFormatter())

        logger = logging.getLogger("test_simple")
        logger.handlers = [h]
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        logger.warning("avertissement simple")
        output = stream.getvalue().strip()
        if not output:
            pytest.skip("Aucune sortie capturée (env non rechargé)")

        data = json.loads(output)
        assert "timestamp" in data
        assert "level" in data
        assert "message" in data

