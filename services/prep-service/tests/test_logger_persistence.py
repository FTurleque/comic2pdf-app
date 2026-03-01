"""
Tests de persistance et rotation des logs pour le prep-service.
Vérifie :
  - création du fichier de log dans LOG_DIR (tmp_path)
  - déclenchement de la rotation
  - validité JSON quand LOG_JSON=true
  - isolation complète via importlib.reload + reset_logger_for_tests
"""
import importlib
import json
import logging
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def _reload_logger_module(monkeypatch, tmp_path, **env_overrides):
    """
    Recharge app.logger en injectant les variables d'environnement souhaitées.

    :param monkeypatch: Fixture pytest pour les variables d'env.
    :param tmp_path: Répertoire temporaire pytest.
    :param env_overrides: Paires clé/valeur supplémentaires.
    :return: Module app.logger rechargé.
    """
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_FILE", "prep-service.log")
    monkeypatch.setenv("LOG_ROTATE_MAX_BYTES", env_overrides.get("LOG_ROTATE_MAX_BYTES", "10000000"))
    monkeypatch.setenv("LOG_ROTATE_BACKUPS", env_overrides.get("LOG_ROTATE_BACKUPS", "5"))
    monkeypatch.setenv("LOG_JSON", env_overrides.get("LOG_JSON", "false"))
    monkeypatch.setenv("LOG_LEVEL", env_overrides.get("LOG_LEVEL", "INFO"))

    import app.logger as mod
    importlib.reload(mod)
    return mod


class TestPrepLoggerFileCreation:

    def test_fichier_log_cree(self, monkeypatch, tmp_path):
        """Après get_logger + un message, le fichier de log doit exister dans LOG_DIR."""
        mod = _reload_logger_module(monkeypatch, tmp_path)

        logger = mod.get_logger("test_prep_creation")
        try:
            logger.info("prep message de test")
            log_file = tmp_path / "prep-service.log"
            assert log_file.exists(), f"Fichier de log absent : {log_file}"
            assert log_file.stat().st_size > 0
        finally:
            mod.reset_logger_for_tests(logger)

    def test_deux_handlers(self, monkeypatch, tmp_path):
        """get_logger doit attacher exactement 2 handlers."""
        import logging.handlers as lh
        mod = _reload_logger_module(monkeypatch, tmp_path)

        logger = mod.get_logger("test_prep_handlers")
        try:
            assert len(logger.handlers) == 2
            types = {type(h) for h in logger.handlers}
            assert logging.StreamHandler in types
            assert lh.RotatingFileHandler in types
        finally:
            mod.reset_logger_for_tests(logger)


class TestPrepLoggerRotation:

    def test_rotation_fichier_point_1_cree(self, monkeypatch, tmp_path):
        """Après dépassement de maxBytes, prep-service.log.1 doit être créé."""
        mod = _reload_logger_module(
            monkeypatch, tmp_path,
            LOG_ROTATE_MAX_BYTES="200",
            LOG_ROTATE_BACKUPS="3",
        )

        logger = mod.get_logger("test_prep_rotation")
        try:
            message = "P" * 80
            for _ in range(10):
                logger.info(message)
            for h in logger.handlers:
                h.flush()

            rotated = tmp_path / "prep-service.log.1"
            assert rotated.exists(), (
                f"Fichier rotatif prep-service.log.1 absent. "
                f"Contenu : {list(tmp_path.iterdir())}"
            )
        finally:
            mod.reset_logger_for_tests(logger)


class TestPrepLoggerJsonFormat:

    def test_ligne_json_valide(self, monkeypatch, tmp_path):
        """Avec LOG_JSON=true, chaque ligne du fichier est un JSON valide."""
        mod = _reload_logger_module(monkeypatch, tmp_path, LOG_JSON="true")

        logger = mod.get_logger("test_prep_json")
        try:
            logger.info("prep json message")
            for h in logger.handlers:
                h.flush()

            log_file = tmp_path / "prep-service.log"
            lines = [l.strip() for l in log_file.read_text(encoding="utf-8").splitlines() if l.strip()]
            assert lines, "Fichier de log vide"
            for line in lines:
                data = json.loads(line)
                assert "timestamp" in data
                assert "level" in data
                assert "service" in data
                assert "message" in data
        finally:
            mod.reset_logger_for_tests(logger)

    def test_json_service_name(self, monkeypatch, tmp_path):
        """Le champ service doit valoir 'prep-service' dans les logs JSON."""
        mod = _reload_logger_module(monkeypatch, tmp_path, LOG_JSON="true")

        logger = mod.get_logger("test_prep_service_name")
        try:
            logger.info("check service name")
            for h in logger.handlers:
                h.flush()

            log_file = tmp_path / "prep-service.log"
            lines = [l.strip() for l in log_file.read_text(encoding="utf-8").splitlines() if l.strip()]
            data = json.loads(lines[0])
            assert data["service"] == "prep-service"
        finally:
            mod.reset_logger_for_tests(logger)


class TestPrepResetLogger:

    def test_reset_supprime_tous_les_handlers(self, monkeypatch, tmp_path):
        """reset_logger_for_tests doit vider la liste des handlers."""
        mod = _reload_logger_module(monkeypatch, tmp_path)

        logger = mod.get_logger("test_prep_reset")
        assert len(logger.handlers) == 2
        mod.reset_logger_for_tests(logger)
        assert len(logger.handlers) == 0

