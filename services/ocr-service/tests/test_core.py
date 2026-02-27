"""
Tests unitaires du ocr-service — versions outils, construction commande, requeue.
Aucun outil externe requis (subprocess mocké).
"""
import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.core import get_tool_versions, build_ocrmypdf_cmd, requeue_running


# ---------------------------------------------------------------------------
# Versions des outils
# ---------------------------------------------------------------------------

class TestGetToolVersions:
    """Vérification de get_tool_versions avec subprocess mocké."""

    def _make_completed(self, stdout="", stderr="", returncode=0):
        m = MagicMock()
        m.stdout = stdout
        m.stderr = stderr
        m.returncode = returncode
        return m

    def test_toutes_les_cles_presentes(self):
        """Le dict retourné contient bien ocrmypdf, tesseract, ghostscript."""
        result = MagicMock()
        result.stdout = "ocrmypdf 14.0.0\n"
        result.stderr = ""

        result2 = MagicMock()
        result2.stdout = "tesseract 5.3.0\n"
        result2.stderr = ""

        result3 = MagicMock()
        result3.stdout = "10.01.1\n"
        result3.stderr = ""

        with patch("app.core.subprocess.run", side_effect=[result, result2, result3]):
            versions = get_tool_versions()

        assert "ocrmypdf" in versions
        assert "tesseract" in versions
        assert "ghostscript" in versions

    def test_valeurs_factices_correctement_lues(self):
        """Les versions factices sont extraites de la première ligne de stdout."""
        def fake_run(cmd, **kwargs):
            m = MagicMock()
            if "ocrmypdf" in cmd:
                m.stdout = "ocrmypdf 99.0\n"
                m.stderr = ""
            elif "tesseract" in cmd:
                m.stdout = "tesseract 5.0\nother line\n"
                m.stderr = ""
            elif "gs" in cmd:
                m.stdout = "42.0\n"
                m.stderr = ""
            return m

        with patch("app.core.subprocess.run", side_effect=fake_run):
            versions = get_tool_versions()

        assert versions["ocrmypdf"] == "ocrmypdf 99.0"
        assert versions["tesseract"] == "tesseract 5.0"
        assert versions["ghostscript"] == "42.0"

    def test_outil_absent_retourne_unknown(self):
        """Si subprocess lève FileNotFoundError, la version vaut 'unknown'."""
        with patch("app.core.subprocess.run", side_effect=FileNotFoundError("no such file")):
            versions = get_tool_versions()

        assert versions["ocrmypdf"] == "unknown"
        assert versions["tesseract"] == "unknown"
        assert versions["ghostscript"] == "unknown"


# ---------------------------------------------------------------------------
# Construction de la commande ocrmypdf
# ---------------------------------------------------------------------------

class TestBuildOcrmypdfCmd:
    """Vérifications de la construction de la commande ocrmypdf."""

    def test_commande_minimale_tous_flags_actifs(self):
        """Avec les paramètres par défaut, la commande contient les flags attendus."""
        cmd = build_ocrmypdf_cmd("/in/raw.pdf", "/out/final.pdf")
        assert cmd[0] == "ocrmypdf"
        assert "--rotate-pages" in cmd
        assert "--deskew" in cmd
        assert "--optimize" in cmd
        assert "1" in cmd
        assert "-l" in cmd
        assert "fra+eng" in cmd
        assert "/in/raw.pdf" in cmd
        assert "/out/final.pdf" in cmd

    def test_rotate_desactive(self):
        """Avec rotate=False, --rotate-pages est absent."""
        cmd = build_ocrmypdf_cmd("/in/raw.pdf", "/out/final.pdf", rotate=False)
        assert "--rotate-pages" not in cmd

    def test_deskew_desactive(self):
        """Avec deskew=False, --deskew est absent."""
        cmd = build_ocrmypdf_cmd("/in/raw.pdf", "/out/final.pdf", deskew=False)
        assert "--deskew" not in cmd

    def test_langue_personnalisee(self):
        """La langue passée est bien injectée dans la commande."""
        cmd = build_ocrmypdf_cmd("/in/raw.pdf", "/out/final.pdf", lang="deu")
        idx = cmd.index("-l")
        assert cmd[idx + 1] == "deu"

    def test_optimize_niveau_0(self):
        """optimize=0 est bien passé à la commande."""
        cmd = build_ocrmypdf_cmd("/in/raw.pdf", "/out/final.pdf", optimize=0)
        idx = cmd.index("--optimize")
        assert cmd[idx + 1] == "0"

    def test_source_et_dest_en_fin_de_commande(self):
        """Source et destination sont les deux derniers arguments."""
        cmd = build_ocrmypdf_cmd("/src.pdf", "/dst.pdf")
        assert cmd[-2] == "/src.pdf"
        assert cmd[-1] == "/dst.pdf"


# ---------------------------------------------------------------------------
# Requeue au démarrage
# ---------------------------------------------------------------------------

class TestRequeuRunning:
    """Vérifications du requeue des jobs RUNNING au boot."""

    def test_requeue_deplace_json_vers_queue(self, tmp_path):
        """Un .json dans running/ est déplacé vers queue/."""
        running_dir = tmp_path / "running"
        queue_dir = tmp_path / "queue"
        running_dir.mkdir()
        queue_dir.mkdir()

        job_file = running_dir / "abc123.json"
        job_file.write_text('{"jobId": "abc123", "state": "RUNNING"}')

        count = requeue_running(str(running_dir), str(queue_dir))

        assert count == 1
        assert not (running_dir / "abc123.json").exists()
        assert (queue_dir / "abc123.json").exists()

    def test_requeue_ignore_non_json(self, tmp_path):
        """Les fichiers non-.json sont ignorés."""
        running_dir = tmp_path / "running"
        queue_dir = tmp_path / "queue"
        running_dir.mkdir()
        queue_dir.mkdir()

        (running_dir / "log.txt").write_text("not a job")

        count = requeue_running(str(running_dir), str(queue_dir))
        assert count == 0
        assert (running_dir / "log.txt").exists()

    def test_requeue_multiple_jobs(self, tmp_path):
        """Plusieurs jobs en running sont tous remis en queue."""
        running_dir = tmp_path / "running"
        queue_dir = tmp_path / "queue"
        running_dir.mkdir()
        queue_dir.mkdir()

        for i in range(3):
            (running_dir / f"job{i}.json").write_text(f'{{"jobId": "job{i}"}}')

        count = requeue_running(str(running_dir), str(queue_dir))
        assert count == 3
        assert len(list(queue_dir.iterdir())) == 3

    def test_running_vide_retourne_zero(self, tmp_path):
        """Un dossier running vide retourne 0."""
        running_dir = tmp_path / "running"
        queue_dir = tmp_path / "queue"
        running_dir.mkdir()
        queue_dir.mkdir()

        count = requeue_running(str(running_dir), str(queue_dir))
        assert count == 0

