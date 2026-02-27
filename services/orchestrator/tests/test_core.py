"""
Tests unitaires du core de l'orchestrateur :
profil canonique, jobKey, heartbeat, métriques.
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.core import (
    canonical_profile,
    stable_json,
    make_job_key,
    is_heartbeat_stale,
    make_empty_metrics,
    update_metrics,
    write_metrics,
)


# ---------------------------------------------------------------------------
# Profil canonique + déterminisme du hash
# ---------------------------------------------------------------------------

class TestCanonicalProfile:
    """Vérifications du profil canonique et de son déterminisme."""

    def _make_infos(self):
        prep_info = {"service": "prep-service", "versions": {"7z": "23.01", "img2pdf": "0.5.1"}}
        ocr_info = {"service": "ocr-service", "versions": {
            "ocrmypdf": "14.0.0",
            "tesseract": "5.3.0",
            "ghostscript": "10.01.1",
        }}
        return prep_info, ocr_info

    def test_profil_contient_versions_outils(self):
        """Le profil inclut bien les versions des outils prep et ocr."""
        prep_info, ocr_info = self._make_infos()
        profile = canonical_profile(prep_info, ocr_info)
        assert profile["prep"]["tools"]["7z"] == "23.01"
        assert profile["ocr"]["tools"]["ocrmypdf"] == "14.0.0"

    def test_stable_json_deterministe(self):
        """stable_json produit le même résultat pour le même dict, peu importe l'ordre des clés."""
        d1 = {"b": 2, "a": 1}
        d2 = {"a": 1, "b": 2}
        assert stable_json(d1) == stable_json(d2)

    def test_hash_profil_identique_pour_meme_input(self):
        """Deux appels identiques produisent le même profileHash."""
        prep_info, ocr_info = self._make_infos()
        profile1 = canonical_profile(prep_info, ocr_info, "fra+eng")
        profile2 = canonical_profile(prep_info, ocr_info, "fra+eng")
        _, jk1 = make_job_key("abc123", profile1)
        _, jk2 = make_job_key("abc123", profile2)
        assert jk1 == jk2

    def test_langue_normalisee_meme_hash(self):
        """'eng+fra' et 'fra+eng' produisent le même profil (tri des tokens)."""
        prep_info, ocr_info = self._make_infos()
        profile_a = canonical_profile(prep_info, ocr_info, "fra+eng")
        profile_b = canonical_profile(prep_info, ocr_info, "eng+fra")
        assert stable_json(profile_a) == stable_json(profile_b)

    def test_profil_change_si_version_outil_change(self):
        """Si la version d'un outil change, le profileHash change."""
        prep_info, ocr_info = self._make_infos()
        profile_v1 = canonical_profile(prep_info, ocr_info)

        ocr_info_v2 = dict(ocr_info)
        ocr_info_v2["versions"] = dict(ocr_info["versions"])
        ocr_info_v2["versions"]["ocrmypdf"] = "15.0.0"
        profile_v2 = canonical_profile(prep_info, ocr_info_v2)

        assert stable_json(profile_v1) != stable_json(profile_v2)


# ---------------------------------------------------------------------------
# make_job_key
# ---------------------------------------------------------------------------

class TestMakeJobKey:
    """Vérifications du calcul de jobKey."""

    def _profile(self):
        return canonical_profile(
            {"versions": {"7z": "1.0"}},
            {"versions": {"ocrmypdf": "1.0", "tesseract": "1.0", "ghostscript": "1.0"}},
        )

    def test_jobkey_change_si_fichier_change(self):
        """Un hash de fichier différent produit un jobKey différent."""
        profile = self._profile()
        _, jk1 = make_job_key("hash_aaa", profile)
        _, jk2 = make_job_key("hash_bbb", profile)
        assert jk1 != jk2

    def test_jobkey_change_si_profil_change(self):
        """Un profil différent produit un jobKey différent pour le même fichier."""
        profile1 = canonical_profile(
            {"versions": {"7z": "1.0"}},
            {"versions": {"ocrmypdf": "1.0", "tesseract": "1.0", "ghostscript": "1.0"}},
        )
        profile2 = canonical_profile(
            {"versions": {"7z": "2.0"}},  # version 7z différente
            {"versions": {"ocrmypdf": "1.0", "tesseract": "1.0", "ghostscript": "1.0"}},
        )
        _, jk1 = make_job_key("same_hash", profile1)
        _, jk2 = make_job_key("same_hash", profile2)
        assert jk1 != jk2

    def test_jobkey_format_double_underscore(self):
        """Le jobKey est de la forme fileHash__profileHash."""
        profile = self._profile()
        _, jk = make_job_key("filehash123", profile)
        assert "__" in jk
        parts = jk.split("__")
        assert len(parts) == 2
        assert parts[0] == "filehash123"

    def test_jobkey_deterministe(self):
        """Même entrée -> même jobKey."""
        profile = self._profile()
        _, jk1 = make_job_key("same", profile)
        _, jk2 = make_job_key("same", profile)
        assert jk1 == jk2


# ---------------------------------------------------------------------------
# Heartbeat
# ---------------------------------------------------------------------------

class TestIsHeartbeatStale:
    """Vérifications de la détection de heartbeats périmés."""

    def test_heartbeat_recent_non_stale(self, tmp_path):
        """Un heartbeat écrit il y a 1 seconde n'est pas stale (timeout=60)."""
        hb = tmp_path / "test.heartbeat"
        hb.write_text("2026-01-01T00:00:00Z start\n")
        # Forcer la mtime à now
        os.utime(str(hb), None)
        assert not is_heartbeat_stale(str(hb), timeout_s=60)

    def test_heartbeat_vieux_est_stale(self, tmp_path):
        """Un heartbeat dont la mtime est trop ancienne est stale."""
        hb = tmp_path / "old.heartbeat"
        hb.write_text("vieux\n")
        # Simuler un heartbeat vieux de 700 secondes
        old_time = time.time() - 700
        os.utime(str(hb), (old_time, old_time))
        assert is_heartbeat_stale(str(hb), timeout_s=600)

    def test_heartbeat_absent_avec_timeout_zero_est_stale(self, tmp_path):
        """Un heartbeat absent est stale si absent_timeout_s=0."""
        hb_path = str(tmp_path / "absent.heartbeat")
        assert is_heartbeat_stale(hb_path, timeout_s=60, absent_timeout_s=0)

    def test_heartbeat_absent_avec_timeout_positif_non_stale(self, tmp_path):
        """Un heartbeat absent n'est pas stale si absent_timeout_s > 0."""
        hb_path = str(tmp_path / "absent2.heartbeat")
        assert not is_heartbeat_stale(hb_path, timeout_s=60, absent_timeout_s=120)


# ---------------------------------------------------------------------------
# Métriques
# ---------------------------------------------------------------------------

class TestMetrics:
    """Vérifications des fonctions de métriques."""

    def test_metriques_initiales_a_zero(self):
        """make_empty_metrics retourne des compteurs à 0."""
        m = make_empty_metrics()
        assert m["done"] == 0
        assert m["error"] == 0
        assert m["running"] == 0
        assert m["queued"] == 0

    def test_update_incremente_compteur_done(self):
        """update_metrics("done") incrémente uniquement le compteur done."""
        m = make_empty_metrics()
        update_metrics(m, "done")
        assert m["done"] == 1
        assert m["error"] == 0

    def test_update_incremente_compteur_error(self):
        """update_metrics("error") incrémente uniquement le compteur error."""
        m = make_empty_metrics()
        update_metrics(m, "error")
        assert m["error"] == 1
        assert m["done"] == 0

    def test_update_evenement_inconnu_ignore(self):
        """Un événement inconnu est ignoré (aucun crash)."""
        m = make_empty_metrics()
        result = update_metrics(m, "evenement_inconnu")
        assert result["done"] == 0

    def test_write_metrics_cree_fichier_json(self, tmp_path):
        """write_metrics crée bien metrics.json dans index_dir."""
        m = make_empty_metrics()
        update_metrics(m, "done")
        update_metrics(m, "done")
        update_metrics(m, "error")

        path = write_metrics(m, str(tmp_path))
        assert os.path.exists(path)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        assert data["done"] == 2
        assert data["error"] == 1
        assert "updatedAt" in data

    def test_write_metrics_cree_dossier_si_absent(self, tmp_path):
        """write_metrics crée index_dir s'il n'existe pas encore."""
        index_dir = str(tmp_path / "nouveau_dossier" / "index")
        m = make_empty_metrics()
        write_metrics(m, index_dir)
        assert os.path.exists(os.path.join(index_dir, "metrics.json"))

