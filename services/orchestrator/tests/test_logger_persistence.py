"""
Tests de persistance et rotation des logs pour l'orchestrateur.
Vérifie :
  - création du fichier de log dans LOG_DIR (tmp_path)
  - déclenchement de la rotation quand LOG_ROTATE_MAX_BYTES est dépassé
  - validité JSON de chaque ligne quand LOG_JSON=true
  - isolation complète : importlib.reload + reset_logger_for_tests
"""
import importlib
import json
import logging
import os
import sys

import pytest

# Ajout de la racine du service dans sys.path (géré par conftest.py, mais explicite ici pour clarté)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reload_logger_module(monkeypatch, tmp_path, **env_overrides):
    """
    Recharge app.logger en injectant les variables d'environnement souhaitées
    et en pointant LOG_DIR vers tmp_path.

    :param monkeypatch: Fixture pytest pour les variables d'env.
    :param tmp_path: Répertoire temporaire pytest.
    :param env_overrides: Paires clé/valeur supplémentaires à injecter dans os.environ.
    :return: Module app.logger rechargé.
    """
    monkeypatch.setenv("LOG_DIR", str(tmp_path))
    monkeypatch.setenv("LOG_FILE", "orchestrator.log")
    monkeypatch.setenv("LOG_ROTATE_MAX_BYTES", env_overrides.get("LOG_ROTATE_MAX_BYTES", "10000000"))
    monkeypatch.setenv("LOG_ROTATE_BACKUPS", env_overrides.get("LOG_ROTATE_BACKUPS", "5"))
    monkeypatch.setenv("LOG_JSON", env_overrides.get("LOG_JSON", "false"))
    monkeypatch.setenv("LOG_LEVEL", env_overrides.get("LOG_LEVEL", "INFO"))

    import app.logger as mod
    importlib.reload(mod)
    return mod


# ---------------------------------------------------------------------------
# Tests : création du fichier de log
# ---------------------------------------------------------------------------

class TestLoggerFileCreation:

    def test_fichier_log_cree_dans_log_dir(self, monkeypatch, tmp_path):
        """Après get_logger + un message, le fichier de log doit exister dans LOG_DIR."""
        mod = _reload_logger_module(monkeypatch, tmp_path)

        logger = mod.get_logger("test_creation")
        try:
            logger.info("message de test")
            log_file = tmp_path / "orchestrator.log"
            assert log_file.exists(), f"Fichier de log absent : {log_file}"
            assert log_file.stat().st_size > 0
        finally:
            mod.reset_logger_for_tests(logger)

    def test_log_dir_cree_automatiquement(self, monkeypatch, tmp_path):
        """LOG_DIR est créé automatiquement s'il n'existe pas."""
        nested = tmp_path / "sous" / "dossier"
        monkeypatch.setenv("LOG_DIR", str(nested))
        monkeypatch.setenv("LOG_FILE", "orchestrator.log")
        monkeypatch.setenv("LOG_ROTATE_MAX_BYTES", "10000000")
        monkeypatch.setenv("LOG_ROTATE_BACKUPS", "5")
        monkeypatch.setenv("LOG_JSON", "false")
        monkeypatch.setenv("LOG_LEVEL", "INFO")

        import app.logger as mod
        importlib.reload(mod)

        logger = mod.get_logger("test_mkdir")
        try:
            logger.info("test création dossier")
            assert (nested / "orchestrator.log").exists()
        finally:
            mod.reset_logger_for_tests(logger)

    def test_deux_handlers_stdout_et_fichier(self, monkeypatch, tmp_path):
        """get_logger doit attacher exactement 2 handlers : StreamHandler + RotatingFileHandler."""
        import logging.handlers as lh
        mod = _reload_logger_module(monkeypatch, tmp_path)

        logger = mod.get_logger("test_handlers")
        try:
            assert len(logger.handlers) == 2
            types = {type(h) for h in logger.handlers}
            assert logging.StreamHandler in types
            assert lh.RotatingFileHandler in types
        finally:
            mod.reset_logger_for_tests(logger)


# ---------------------------------------------------------------------------
# Tests : rotation
# ---------------------------------------------------------------------------

class TestLoggerRotation:

    def test_rotation_fichier_point_1_cree(self, monkeypatch, tmp_path):
        """Après dépassement de maxBytes, orchestrator.log.1 doit être créé."""
        mod = _reload_logger_module(
            monkeypatch, tmp_path,
            LOG_ROTATE_MAX_BYTES="200",
            LOG_ROTATE_BACKUPS="3",
        )

        logger = mod.get_logger("test_rotation")
        try:
            # Écrire suffisamment pour déclencher la rotation
            message = "A" * 80
            for _ in range(10):
                logger.info(message)

            # Forcer le flush de tous les handlers
            for h in logger.handlers:
                h.flush()

            rotated = tmp_path / "orchestrator.log.1"
            assert rotated.exists(), (
                f"Fichier rotatif orchestrator.log.1 absent. "
                f"Contenu de tmp_path : {list(tmp_path.iterdir())}"
            )
        finally:
            mod.reset_logger_for_tests(logger)

    def test_rotation_plusieurs_fichiers(self, monkeypatch, tmp_path):
        """Avec backupCount=2, orchestrator.log.1 et orchestrator.log.2 peuvent apparaître."""
        mod = _reload_logger_module(
            monkeypatch, tmp_path,
            LOG_ROTATE_MAX_BYTES="100",
            LOG_ROTATE_BACKUPS="2",
        )

        logger = mod.get_logger("test_rotation_multi")
        try:
            message = "B" * 60
            for _ in range(20):
                logger.info(message)

            for h in logger.handlers:
                h.flush()

            existing = list(tmp_path.iterdir())
            log_names = {f.name for f in existing}
            # Au moins orchestrator.log doit exister
            assert "orchestrator.log" in log_names
            # Au moins un fichier rotatif doit avoir été créé
            rotated = {n for n in log_names if n.startswith("orchestrator.log.")}
            assert len(rotated) >= 1, f"Aucun fichier rotatif trouvé. Fichiers : {log_names}"
        finally:
            mod.reset_logger_for_tests(logger)

    def test_get_logger_idempotent_pas_double_handler(self, monkeypatch, tmp_path):
        """Appeler get_logger deux fois avec le même nom ne doit pas doubler les handlers."""
        mod = _reload_logger_module(monkeypatch, tmp_path)

        logger1 = mod.get_logger("test_idempotent")
        logger2 = mod.get_logger("test_idempotent")
        try:
            assert logger1 is logger2
            assert len(logger1.handlers) == 2
        finally:
            mod.reset_logger_for_tests(logger1)


# ---------------------------------------------------------------------------
# Tests : format JSON
# ---------------------------------------------------------------------------

class TestLoggerJsonFormat:

    def test_ligne_json_valide(self, monkeypatch, tmp_path):
        """Avec LOG_JSON=true, chaque ligne du fichier de log est un JSON valide."""
        mod = _reload_logger_module(monkeypatch, tmp_path, LOG_JSON="true")

        logger = mod.get_logger("test_json")
        try:
            logger.info("message json test")

            for h in logger.handlers:
                h.flush()

            log_file = tmp_path / "orchestrator.log"
            lines = [l.strip() for l in log_file.read_text(encoding="utf-8").splitlines() if l.strip()]
            assert len(lines) >= 1, "Aucune ligne dans le fichier de log"

            for line in lines:
                data = json.loads(line)
                assert "timestamp" in data
                assert "level" in data
                assert "service" in data
                assert "message" in data
        finally:
            mod.reset_logger_for_tests(logger)

    def test_json_champs_obligatoires(self, monkeypatch, tmp_path):
        """Les champs timestamp, level, service, message sont présents dans chaque ligne JSON."""
        mod = _reload_logger_module(monkeypatch, tmp_path, LOG_JSON="true")

        logger = mod.get_logger("test_json_champs")
        try:
            logger.warning("avertissement test", extra={"jobKey": "abc123", "stage": "PREP"})

            for h in logger.handlers:
                h.flush()

            log_file = tmp_path / "orchestrator.log"
            lines = [l.strip() for l in log_file.read_text(encoding="utf-8").splitlines() if l.strip()]
            assert lines, "Fichier de log vide"

            data = json.loads(lines[0])
            assert data["level"] == "WARNING"
            assert data["service"] == "orchestrator"
            assert data["message"] == "avertissement test"
            assert data.get("jobKey") == "abc123"
            assert data.get("stage") == "PREP"
        finally:
            mod.reset_logger_for_tests(logger)

    def test_json_rotation_ligne_valide_apres_rotation(self, monkeypatch, tmp_path):
        """Après rotation, les nouvelles lignes du fichier courant restent du JSON valide."""
        mod = _reload_logger_module(
            monkeypatch, tmp_path,
            LOG_JSON="true",
            LOG_ROTATE_MAX_BYTES="300",
            LOG_ROTATE_BACKUPS="2",
        )

        logger = mod.get_logger("test_json_rotation")
        try:
            for i in range(15):
                logger.info(f"message {i}")

            for h in logger.handlers:
                h.flush()

            log_file = tmp_path / "orchestrator.log"
            assert log_file.exists()
            lines = [l.strip() for l in log_file.read_text(encoding="utf-8").splitlines() if l.strip()]
            for line in lines:
                json.loads(line)  # doit être du JSON valide, sinon exception
        finally:
            mod.reset_logger_for_tests(logger)

    def test_format_texte_par_defaut(self, monkeypatch, tmp_path):
        """Sans LOG_JSON=true, le fichier de log contient du texte lisible (pas du JSON)."""
        mod = _reload_logger_module(monkeypatch, tmp_path, LOG_JSON="false")

        logger = mod.get_logger("test_text_format")
        try:
            logger.info("message texte")

            for h in logger.handlers:
                h.flush()

            log_file = tmp_path / "orchestrator.log"
            content = log_file.read_text(encoding="utf-8")
            assert "message texte" in content
            # En mode texte, la ligne ne doit pas commencer par '{'
            first_line = content.strip().splitlines()[0]
            assert not first_line.startswith("{"), "La ligne ne devrait pas être du JSON en mode texte"
        finally:
            mod.reset_logger_for_tests(logger)


# ---------------------------------------------------------------------------
# Tests : isolation reset_logger_for_tests
# ---------------------------------------------------------------------------

class TestResetLoggerForTests:

    def test_reset_supprime_tous_les_handlers(self, monkeypatch, tmp_path):
        """reset_logger_for_tests doit vider la liste des handlers."""
        mod = _reload_logger_module(monkeypatch, tmp_path)

        logger = mod.get_logger("test_reset")
        assert len(logger.handlers) == 2
        mod.reset_logger_for_tests(logger)
        assert len(logger.handlers) == 0

    def test_reset_permet_reinitialisation(self, monkeypatch, tmp_path):
        """Après reset, get_logger doit pouvoir réinitialiser proprement le logger."""
        mod = _reload_logger_module(monkeypatch, tmp_path)

        logger = mod.get_logger("test_reinit")
        mod.reset_logger_for_tests(logger)
        assert len(logger.handlers) == 0

        # Après un reload et reset, on peut réinitialiser proprement
        mod2 = _reload_logger_module(monkeypatch, tmp_path)
        logger2 = mod2.get_logger("test_reinit_2")
        try:
            assert len(logger2.handlers) == 2
        finally:
            mod2.reset_logger_for_tests(logger2)

