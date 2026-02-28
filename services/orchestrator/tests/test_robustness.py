"""
Tests de robustesse FS pour l'orchestrateur :
- validate_pdf (OK/KO)
- check_disk_space (mock disk_usage)
- check_input_size (taille)
- check_file_signature (ZIP/RAR/invalide)
- cleanup_old_workdirs (ancien/récent/running)
Aucun outil externe requis.
"""
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch

from app.utils import (
    validate_pdf,
    check_disk_space,
    check_input_size,
    check_file_signature,
    cleanup_old_workdirs,
)


# ---------------------------------------------------------------------------
# validate_pdf
# ---------------------------------------------------------------------------

class TestValidatePdf:

    def test_pdf_valide_header_et_taille(self, tmp_path):
        """Un fichier avec header %PDF- et taille suffisante est accepté."""
        p = tmp_path / "ok.pdf"
        p.write_bytes(b"%PDF-1.4\n" + b"x" * 2048)
        assert validate_pdf(str(p), min_size_bytes=512) is True

    def test_pdf_header_incorrect_rejete(self, tmp_path):
        """Un fichier sans header %PDF- est rejeté."""
        p = tmp_path / "bad.pdf"
        p.write_bytes(b"NOTPDF\n" + b"x" * 2048)
        assert validate_pdf(str(p), min_size_bytes=512) is False

    def test_pdf_trop_petit_rejete(self, tmp_path):
        """Un PDF valide mais trop petit est rejeté."""
        p = tmp_path / "tiny.pdf"
        p.write_bytes(b"%PDF-1.4\n" + b"x" * 10)
        assert validate_pdf(str(p), min_size_bytes=1024) is False

    def test_pdf_absent_rejete(self, tmp_path):
        """Un fichier inexistant retourne False."""
        assert validate_pdf(str(tmp_path / "absent.pdf")) is False

    def test_pdf_vide_rejete(self, tmp_path):
        """Un fichier vide retourne False."""
        p = tmp_path / "empty.pdf"
        p.write_bytes(b"")
        assert validate_pdf(str(p), min_size_bytes=1) is False


# ---------------------------------------------------------------------------
# check_disk_space
# ---------------------------------------------------------------------------

class TestCheckDiskSpace:

    def test_espace_suffisant_retourne_true(self, tmp_path):
        """Si l'espace libre est supérieur au besoin, retourne True."""
        import shutil
        real_free = shutil.disk_usage(str(tmp_path)).free
        # Le fichier fait 1 octet : même avec factor=2.0, c'est largement OK
        assert check_disk_space(str(tmp_path), 1, factor=2.0) is True

    def test_espace_insuffisant_retourne_false(self, tmp_path):
        """Si disk_usage retourne peu d'espace libre, retourne False."""
        mock_usage = type("Usage", (), {"free": 100})()
        with patch("app.utils.shutil.disk_usage", return_value=mock_usage):
            result = check_disk_space(str(tmp_path), 1000, factor=2.0)
        assert result is False

    def test_erreur_disk_usage_retourne_true(self, tmp_path):
        """En cas d'exception disk_usage, on laisse passer (True)."""
        with patch("app.utils.shutil.disk_usage", side_effect=OSError("disk error")):
            result = check_disk_space(str(tmp_path), 1000, factor=2.0)
        assert result is True


# ---------------------------------------------------------------------------
# check_input_size
# ---------------------------------------------------------------------------

class TestCheckInputSize:

    def test_fichier_dans_les_limites_accepte(self, tmp_path):
        """Un fichier de 1 Mo est accepté avec max_mb=500."""
        p = tmp_path / "ok.cbz"
        p.write_bytes(b"x" * (1024 * 1024))  # 1 Mo
        assert check_input_size(str(p), max_mb=500) is True

    def test_fichier_trop_grand_rejete(self, tmp_path):
        """Un fichier dépassant la limite est rejeté."""
        p = tmp_path / "big.cbz"
        # On mock os.path.getsize pour simuler un gros fichier
        with patch("app.utils.os.path.getsize", return_value=600 * 1024 * 1024):
            result = check_input_size(str(p), max_mb=500)
        assert result is False

    def test_fichier_absent_retourne_false(self, tmp_path):
        """Un fichier inexistant retourne False."""
        assert check_input_size(str(tmp_path / "absent.cbz"), max_mb=500) is False


# ---------------------------------------------------------------------------
# check_file_signature
# ---------------------------------------------------------------------------

class TestCheckFileSignature:

    def test_zip_valide_accepte(self, tmp_path):
        """Un fichier avec la signature ZIP (50 4B 03 04) est accepté."""
        p = tmp_path / "comic.cbz"
        p.write_bytes(b"\x50\x4B\x03\x04" + b"\x00" * 100)
        assert check_file_signature(str(p)) is True

    def test_rar4_valide_accepte(self, tmp_path):
        """Un fichier avec la signature RAR4 est accepté."""
        p = tmp_path / "comic.cbr"
        p.write_bytes(b"\x52\x61\x72\x21\x1A\x07\x00" + b"\x00" * 100)
        assert check_file_signature(str(p)) is True

    def test_rar5_valide_accepte(self, tmp_path):
        """Un fichier avec la signature RAR5 est accepté."""
        p = tmp_path / "comic5.cbr"
        p.write_bytes(b"\x52\x61\x72\x21\x1A\x07\x01\x00" + b"\x00" * 100)
        assert check_file_signature(str(p)) is True

    def test_fichier_texte_rejete(self, tmp_path):
        """Un fichier texte sans signature ZIP/RAR est rejeté."""
        p = tmp_path / "fake.cbz"
        p.write_bytes(b"This is not a zip file!\n" + b"x" * 100)
        assert check_file_signature(str(p)) is False

    def test_pdf_rejete(self, tmp_path):
        """Un fichier PDF est rejeté (signature %PDF non reconnue)."""
        p = tmp_path / "fake.cbz"
        p.write_bytes(b"%PDF-1.4\n" + b"x" * 100)
        assert check_file_signature(str(p)) is False

    def test_fichier_absent_retourne_false(self, tmp_path):
        """Un fichier inexistant retourne False."""
        assert check_file_signature(str(tmp_path / "absent.cbz")) is False


# ---------------------------------------------------------------------------
# cleanup_old_workdirs
# ---------------------------------------------------------------------------

class TestCleanupOldWorkdirs:

    def test_vieux_dossier_supprime(self, tmp_path):
        """Un dossier plus vieux que keep_days est supprimé."""
        old = tmp_path / "old_job_key"
        old.mkdir()
        # Modifier le mtime pour le rendre "vieux"
        old_time = time.time() - (10 * 86400)  # 10 jours dans le passé
        os.utime(str(old), (old_time, old_time))

        deleted = cleanup_old_workdirs(str(tmp_path), keep_days=7, running_job_keys=set())
        assert deleted == 1
        assert not old.exists()

    def test_dossier_recent_conserve(self, tmp_path):
        """Un dossier récent (moins de keep_days jours) est conservé."""
        recent = tmp_path / "recent_job"
        recent.mkdir()
        # mtime = maintenant (récent)

        deleted = cleanup_old_workdirs(str(tmp_path), keep_days=7, running_job_keys=set())
        assert deleted == 0
        assert recent.exists()

    def test_job_running_conserve_meme_si_vieux(self, tmp_path):
        """Un dossier dans running_job_keys n'est jamais supprimé."""
        old = tmp_path / "running_key"
        old.mkdir()
        old_time = time.time() - (20 * 86400)
        os.utime(str(old), (old_time, old_time))

        deleted = cleanup_old_workdirs(str(tmp_path), keep_days=7, running_job_keys={"running_key"})
        assert deleted == 0
        assert old.exists()

    def test_dossier_staging_ignore(self, tmp_path):
        """Les dossiers commençant par '_' (ex: _staging) ne sont jamais supprimés."""
        staging = tmp_path / "_staging"
        staging.mkdir()
        old_time = time.time() - (20 * 86400)
        os.utime(str(staging), (old_time, old_time))

        deleted = cleanup_old_workdirs(str(tmp_path), keep_days=7, running_job_keys=set())
        assert deleted == 0
        assert staging.exists()

    def test_work_dir_absent_retourne_zero(self, tmp_path):
        """Si le work_dir n'existe pas, retourne 0 sans exception."""
        result = cleanup_old_workdirs(str(tmp_path / "absent"), keep_days=7, running_job_keys=set())
        assert result == 0

