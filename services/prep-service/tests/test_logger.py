"""
Tests du module logger — prep-service.
Couvre format JSON, format texte, champs optionnels.
"""
import json
import logging
import os
import sys
from io import StringIO
import importlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def reset_logger():
    """Reset le logger entre les tests pour éviter la pollution."""
    logger = logging.getLogger("prep-service")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)

    yield

    logger.handlers.clear()


@pytest.fixture
def capture_log():
    """Capture la sortie du logger dans un StringIO."""
    stream = StringIO()
    handler = logging.StreamHandler(stream)
    yield stream, handler
    handler.close()


# ---------------------------------------------------------------------------
# Tests format JSON
# ---------------------------------------------------------------------------

class TestLogJsonFormat:
    """Tests du format JSON structuré."""

    def test_log_json_format_structure(self, reset_logger, capture_log, monkeypatch):
        """Le format JSON contient tous les champs requis."""
        monkeypatch.setenv("LOG_JSON", "true")

        # Forcer le rechargement du module logger avec LOG_JSON=true
        import app.logger
        importlib.reload(app.logger)
        from app.logger import get_logger

        stream, handler = capture_log
        logger = get_logger()
        logger.handlers.clear()
        logger.addHandler(handler)

        logger.info("Test message")

        output = stream.getvalue().strip()
        data = json.loads(output)

        assert "timestamp" in data
        assert "level" in data
        assert "service" in data
        assert "message" in data
        assert data["level"] == "INFO"
        assert data["service"] == "prep-service"
        assert data["message"] == "Test message"

    def test_log_json_with_optional_fields(self, reset_logger, capture_log, monkeypatch):
        """Les champs optionnels (jobKey, stage, attempt) sont inclus si présents."""
        monkeypatch.setenv("LOG_JSON", "true")

        import app.logger
        importlib.reload(app.logger)
        from app.logger import get_logger

        stream, handler = capture_log
        logger = get_logger()
        logger.handlers.clear()
        logger.addHandler(handler)

        logger.info("Processing job", extra={"jobKey": "abc123", "stage": "extract", "attempt": 2})

        output = stream.getvalue().strip()
        data = json.loads(output)

        assert data["jobKey"] == "abc123"
        assert data["stage"] == "extract"
        assert data["attempt"] == 2

    def test_log_json_with_exception(self, reset_logger, capture_log, monkeypatch):
        """Les exceptions sont formatées dans le JSON."""
        monkeypatch.setenv("LOG_JSON", "true")

        import app.logger
        importlib.reload(app.logger)
        from app.logger import get_logger

        stream, handler = capture_log
        logger = get_logger()
        logger.handlers.clear()
        logger.addHandler(handler)

        try:
            raise ValueError("Test error")
        except ValueError:
            logger.exception("An error occurred")

        output = stream.getvalue().strip()
        data = json.loads(output)

        assert "exception" in data
        assert "ValueError: Test error" in data["exception"]


# ---------------------------------------------------------------------------
# Tests format texte
# ---------------------------------------------------------------------------

class TestLogTextFormat:
    """Tests du format texte classique."""

    def test_log_text_format(self, reset_logger, capture_log, monkeypatch):
        """Le format texte est utilisé quand LOG_JSON=false."""
        monkeypatch.setenv("LOG_JSON", "false")

        import app.logger
        importlib.reload(app.logger)
        from app.logger import get_logger

        stream, handler = capture_log
        logger = get_logger()
        logger.handlers.clear()
        logger.addHandler(handler)

        logger.info("Test message")

        output = stream.getvalue().strip()

        # Vérifier que ce n'est PAS du JSON
        with pytest.raises(json.JSONDecodeError):
            json.loads(output)

        # Vérifier le format texte
        assert "[INFO]" in output
        assert "prep-service" in output
        assert "Test message" in output

    def test_log_text_default_when_no_env(self, reset_logger, capture_log, monkeypatch):
        """Le format texte est utilisé par défaut si LOG_JSON n'est pas défini."""
        monkeypatch.delenv("LOG_JSON", raising=False)

        import app.logger
        importlib.reload(app.logger)
        from app.logger import get_logger

        stream, handler = capture_log
        logger = get_logger()
        logger.handlers.clear()
        logger.addHandler(handler)

        logger.warning("Warning message")

        output = stream.getvalue().strip()

        # Vérifier format texte
        assert "[WARNING]" in output
        assert "Warning message" in output


# ---------------------------------------------------------------------------
# Tests niveaux de log
# ---------------------------------------------------------------------------

class TestLogLevels:
    """Tests des différents niveaux de log."""

    def test_log_levels(self, reset_logger, capture_log, monkeypatch):
        """Tous les niveaux de log fonctionnent correctement."""
        monkeypatch.setenv("LOG_JSON", "true")

        import app.logger
        importlib.reload(app.logger)
        from app.logger import get_logger

        stream, handler = capture_log
        logger = get_logger()
        logger.handlers.clear()
        logger.addHandler(handler)

        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")

        output = stream.getvalue().strip().split("\n")

        assert len(output) == 4

        levels = [json.loads(line)["level"] for line in output]
        assert levels == ["DEBUG", "INFO", "WARNING", "ERROR"]


# ---------------------------------------------------------------------------
# Tests get_logger
# ---------------------------------------------------------------------------

class TestGetLogger:
    """Tests de la fonction get_logger."""

    def test_get_logger_returns_logger(self, reset_logger, monkeypatch):
        """get_logger retourne une instance de logging.Logger."""
        monkeypatch.setenv("LOG_JSON", "false")

        import app.logger
        importlib.reload(app.logger)
        from app.logger import get_logger

        logger = get_logger()

        assert isinstance(logger, logging.Logger)
        assert logger.name == "prep-service"

    def test_get_logger_with_custom_name(self, reset_logger, monkeypatch):
        """get_logger accepte un nom personnalisé."""
        monkeypatch.setenv("LOG_JSON", "false")

        import app.logger
        importlib.reload(app.logger)
        from app.logger import get_logger

        logger = get_logger("custom-name")

        assert logger.name == "custom-name"

    def test_get_logger_no_duplicate_handlers(self, reset_logger, monkeypatch):
        """get_logger ne crée pas de handlers dupliqués."""
        monkeypatch.setenv("LOG_JSON", "false")

        import app.logger
        importlib.reload(app.logger)
        from app.logger import get_logger

        logger1 = get_logger()
        initial_handlers = len(logger1.handlers)

        logger2 = get_logger()
        final_handlers = len(logger2.handlers)

        assert initial_handlers == final_handlers
        assert logger1 is logger2
