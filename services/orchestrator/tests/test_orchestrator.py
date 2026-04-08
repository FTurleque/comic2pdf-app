"""
Tests unitaires de l'orchestrateur :
doublons, heartbeat-check (check_stale_jobs), process_tick,
check_duplicate_decisions, validation PDF, rejection entrée.
HTTP entièrement mocké.
"""
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from unittest.mock import patch, MagicMock


def _make_config(tmp_path) -> dict:
    """Construit un dict de config minimal pointant vers tmp_path."""
    return {
        "prep_url": "http://mock-prep:8080",
        "ocr_url": "http://mock-ocr:8080",
        "work_dir": str(tmp_path / "work"),
        "max_jobs_in_flight": 3,
        "prep_concurrency": 2,
        "ocr_concurrency": 1,
        "max_attempts_prep": 3,
        "max_attempts_ocr": 3,
        "job_timeout_s": 600,
        "index_dir": str(tmp_path / "index"),
        "metrics": {
            "done": 0,
            "error": 0,
            "running": 0,
            "queued": 0,
            "disk_error": 0,
            "pdf_invalid": 0,
            "input_rejected_size": 0,
            "input_rejected_signature": 0,
            "updatedAt": "",
        },
        "keep_work_dir_days": 7,
        "min_pdf_size_bytes": 1024,
        "disk_free_factor": 2.0,
        "max_input_size_mb": 500,
    }


def _setup_dirs(tmp_path):
    """Crée l'arborescence de données minimale."""
    dirs = [
        "in", "out", "work", "error", "archive",
        "hold/duplicates", "reports/duplicates", "index",
    ]
    for d in dirs:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Doublons
# ---------------------------------------------------------------------------

class TestDoublons:
    """Vérifications de la détection et du traitement des doublons."""

    def test_doublon_place_dans_hold_et_rapport_cree(self, tmp_path, monkeypatch):
        """Un fichier avec un jobKey déjà connu est mis dans hold/duplicates
        et un rapport est créé dans reports/duplicates."""
        import app.main as orch

        _setup_dirs(tmp_path)

        # Patch des répertoires globaux de l'orchestrateur
        monkeypatch.setattr(orch, "IN_DIR", str(tmp_path / "in"))
        monkeypatch.setattr(orch, "WORK_DIR", str(tmp_path / "work"))
        monkeypatch.setattr(orch, "OUT_DIR", str(tmp_path / "out"))
        monkeypatch.setattr(orch, "ERROR_DIR", str(tmp_path / "error"))
        monkeypatch.setattr(orch, "ARCHIVE_DIR", str(tmp_path / "archive"))
        monkeypatch.setattr(orch, "HOLD_DUP_DIR", str(tmp_path / "hold" / "duplicates"))
        monkeypatch.setattr(orch, "DUP_REPORTS_DIR", str(tmp_path / "reports" / "duplicates"))
        monkeypatch.setattr(orch, "INDEX_DIR", str(tmp_path / "index"))

        job_key = "aabbccdd__11223344"
        # Index pré-rempli avec le même jobKey
        existing_entry = {"jobKey": job_key, "state": "DONE", "outPdf": "/out/result.pdf"}

        incoming_path = str(tmp_path / "incoming.cbz")
        with open(incoming_path, "wb") as f:
            f.write(b"fake comic content")

        orch.write_duplicate_report(job_key, incoming_path, existing_entry, {"ocr": {}, "prep": {}})

        # Vérification : le fichier est dans hold/duplicates/<jobKey>/
        hold_dir = tmp_path / "hold" / "duplicates" / job_key
        assert hold_dir.exists()
        held = list(hold_dir.glob("*__incoming.cbz"))
        assert len(held) == 1, "Le fichier entrant doit être dans hold"

        # Vérification : le rapport existe dans reports/duplicates/<jobKey>.json
        report_path = tmp_path / "reports" / "duplicates" / f"{job_key}.json"
        assert report_path.exists(), "Le rapport de doublon doit exister"

        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)

        assert report["jobKey"] == job_key
        assert "incoming" in report
        assert "existing" in report
        assert "USE_EXISTING_RESULT" in report["actions"]

    def test_rapport_contient_champs_requis(self, tmp_path, monkeypatch):
        """Le rapport de doublon contient tous les champs attendus."""
        import app.main as orch

        _setup_dirs(tmp_path)
        monkeypatch.setattr(orch, "HOLD_DUP_DIR", str(tmp_path / "hold" / "duplicates"))
        monkeypatch.setattr(orch, "DUP_REPORTS_DIR", str(tmp_path / "reports" / "duplicates"))

        incoming = str(tmp_path / "comic.cbz")
        with open(incoming, "wb") as f:
            f.write(b"x" * 100)

        job_key = "deadbeef__cafebabe"
        orch.write_duplicate_report(job_key, incoming, {"state": "DONE"}, {"ocr": {}})

        report_path = tmp_path / "reports" / "duplicates" / f"{job_key}.json"
        with open(report_path, "r", encoding="utf-8") as f:
            r = json.load(f)

        for champ in ["jobKey", "detectedAt", "incoming", "existing", "profile", "actions"]:
            assert champ in r, f"Champ manquant : {champ}"

        assert r["incoming"]["sizeBytes"] == 100


# ---------------------------------------------------------------------------
# check_stale_jobs
# ---------------------------------------------------------------------------

class TestCheckStaleJobs:
    """Vérifications de la détection de heartbeats périmés."""

    def test_prep_running_avec_heartbeat_vieux_bascule_en_retry(self, tmp_path, monkeypatch):
        """Un job PREP_RUNNING avec un heartbeat trop vieux bascule en PREP_RETRY."""
        import app.main as orch

        _setup_dirs(tmp_path)
        monkeypatch.setattr(orch, "WORK_DIR", str(tmp_path / "work"))

        job_key = "stalejob_prep_001"
        job_dir = tmp_path / "work" / job_key
        job_dir.mkdir(parents=True)

        # Créer un heartbeat périmé (700 secondes)
        hb_path = job_dir / "prep.heartbeat"
        hb_path.write_text("old heartbeat\n")
        old_time = time.time() - 700
        os.utime(str(hb_path), (old_time, old_time))

        # Créer le state.json pour update_state
        state_path = job_dir / "state.json"
        state_path.write_text(json.dumps({"jobKey": job_key, "state": "PREP_RUNNING"}))

        in_flight = {
            job_key: {
                "stage": "PREP_RUNNING",
                "inputName": "test.cbz",
                "inputPath": str(tmp_path / "work" / job_key / "test.cbz"),
                "attemptPrep": 1,
                "attemptOcr": 0,
            }
        }

        orch.check_stale_jobs(in_flight, timeout_s=600)

        assert in_flight[job_key]["stage"] == "PREP_RETRY", \
            "Le job doit basculer en PREP_RETRY après timeout heartbeat"

    def test_prep_running_avec_heartbeat_recent_reste_running(self, tmp_path, monkeypatch):
        """Un job PREP_RUNNING avec un heartbeat récent reste en PREP_RUNNING."""
        import app.main as orch

        _setup_dirs(tmp_path)
        monkeypatch.setattr(orch, "WORK_DIR", str(tmp_path / "work"))

        job_key = "freshprepjob"
        job_dir = tmp_path / "work" / job_key
        job_dir.mkdir(parents=True)

        hb_path = job_dir / "prep.heartbeat"
        hb_path.write_text("recent heartbeat\n")
        os.utime(str(hb_path), None)  # mtime = now

        state_path = job_dir / "state.json"
        state_path.write_text(json.dumps({"jobKey": job_key, "state": "PREP_RUNNING"}))

        in_flight = {
            job_key: {
                "stage": "PREP_RUNNING",
                "inputName": "test.cbz",
                "inputPath": "",
                "attemptPrep": 1,
                "attemptOcr": 0,
            }
        }

        orch.check_stale_jobs(in_flight, timeout_s=600)

        assert in_flight[job_key]["stage"] == "PREP_RUNNING", \
            "Le job doit rester en PREP_RUNNING si le heartbeat est récent"

    def test_ocr_running_avec_heartbeat_vieux_bascule_en_retry(self, tmp_path, monkeypatch):
        """Un job OCR_RUNNING avec un heartbeat trop vieux bascule en OCR_RETRY."""
        import app.main as orch

        _setup_dirs(tmp_path)
        monkeypatch.setattr(orch, "WORK_DIR", str(tmp_path / "work"))

        job_key = "stalejob_ocr_001"
        job_dir = tmp_path / "work" / job_key
        job_dir.mkdir(parents=True)

        hb_path = job_dir / "ocr.heartbeat"
        hb_path.write_text("old ocr heartbeat\n")
        old_time = time.time() - 700
        os.utime(str(hb_path), (old_time, old_time))

        state_path = job_dir / "state.json"
        state_path.write_text(json.dumps({"jobKey": job_key, "state": "OCR_RUNNING"}))

        in_flight = {
            job_key: {
                "stage": "OCR_RUNNING",
                "inputName": "test.cbz",
                "inputPath": "",
                "attemptPrep": 1,
                "attemptOcr": 1,
                "rawPdf": str(job_dir / "raw.pdf"),
            }
        }

        orch.check_stale_jobs(in_flight, timeout_s=600)

        assert in_flight[job_key]["stage"] == "OCR_RETRY"

    def test_job_discovered_non_affecte(self, tmp_path, monkeypatch):
        """Un job en stage DISCOVERED n'est pas affecté par check_stale_jobs."""
        import app.main as orch

        _setup_dirs(tmp_path)
        monkeypatch.setattr(orch, "WORK_DIR", str(tmp_path / "work"))

        job_key = "discoveredjob"
        job_dir = tmp_path / "work" / job_key
        job_dir.mkdir(parents=True)

        in_flight = {job_key: {"stage": "DISCOVERED", "attemptPrep": 0, "attemptOcr": 0}}

        orch.check_stale_jobs(in_flight, timeout_s=600)

        assert in_flight[job_key]["stage"] == "DISCOVERED"


# ---------------------------------------------------------------------------
# check_duplicate_decisions (P0-ORCH-02)
# ---------------------------------------------------------------------------

def _make_zip_header():
    """Retourne les 4 premiers octets d'une signature ZIP valide."""
    return b"\x50\x4b\x03\x04" + b"\x00" * 100


class TestCheckDuplicateDecisions:
    """Vérifications de l'application des décisions de doublons."""

    def _patch_orch(self, orch, tmp_path, monkeypatch):
        """Patch les répertoires de l'orchestrateur vers tmp_path."""
        monkeypatch.setattr(orch, "IN_DIR", str(tmp_path / "in"))
        monkeypatch.setattr(orch, "WORK_DIR", str(tmp_path / "work"))
        monkeypatch.setattr(orch, "OUT_DIR", str(tmp_path / "out"))
        monkeypatch.setattr(orch, "ERROR_DIR", str(tmp_path / "error"))
        monkeypatch.setattr(orch, "ARCHIVE_DIR", str(tmp_path / "archive"))
        monkeypatch.setattr(orch, "HOLD_DUP_DIR", str(tmp_path / "hold" / "duplicates"))
        monkeypatch.setattr(orch, "DUP_REPORTS_DIR", str(tmp_path / "reports" / "duplicates"))
        monkeypatch.setattr(orch, "INDEX_DIR", str(tmp_path / "index"))

    def test_use_existing_result_copie_pdf_et_archive_entrant(self, tmp_path, monkeypatch):
        """USE_EXISTING_RESULT : le PDF existant est copié dans out/ et l'entrant archivé."""
        import app.main as orch

        _setup_dirs(tmp_path)
        self._patch_orch(orch, tmp_path, monkeypatch)

        job_key = "abcd1234__ef567890"
        hold_dir = tmp_path / "hold" / "duplicates" / job_key
        hold_dir.mkdir(parents=True)

        # Fichier entrant dans hold
        incoming_cbz = hold_dir / "20260101-120000__comic.cbz"
        incoming_cbz.write_bytes(b"fake cbz data")

        # PDF existant dans out
        existing_pdf = tmp_path / "out" / "comic__job-abcd1234__ef567890.pdf"
        existing_pdf.parent.mkdir(parents=True, exist_ok=True)
        existing_pdf.write_bytes(b"%PDF-1.4 existing")

        # Écrire decision.json USE_EXISTING_RESULT
        decision = {"action": "USE_EXISTING_RESULT"}
        (hold_dir / "decision.json").write_text(json.dumps(decision), encoding="utf-8")

        index = {"jobs": {job_key: {"jobKey": job_key, "state": "DONE", "outPdf": str(existing_pdf)}}}
        index_path = str(tmp_path / "index" / "jobs.json")

        orch.check_duplicate_decisions(index, index_path)

        # Le fichier entrant n'est plus dans hold
        assert not incoming_cbz.exists(), "Le fichier entrant doit être supprimé du hold"
        # La décision est nettoyée
        assert not (hold_dir / "decision.json").exists()

    def test_discard_supprime_le_fichier_entrant(self, tmp_path, monkeypatch):
        """DISCARD : le fichier entrant est supprimé, pas de traitement."""
        import app.main as orch

        _setup_dirs(tmp_path)
        self._patch_orch(orch, tmp_path, monkeypatch)

        job_key = "discardkey__1234"
        hold_dir = tmp_path / "hold" / "duplicates" / job_key
        hold_dir.mkdir(parents=True)

        incoming_cbz = hold_dir / "20260101-120000__comic.cbz"
        incoming_cbz.write_bytes(b"fake cbz to discard")

        (hold_dir / "decision.json").write_text(json.dumps({"action": "DISCARD"}), encoding="utf-8")

        index = {"jobs": {job_key: {"jobKey": job_key, "state": "DONE"}}}
        index_path = str(tmp_path / "index" / "jobs.json")

        orch.check_duplicate_decisions(index, index_path)

        assert not incoming_cbz.exists(), "DISCARD doit supprimer le fichier entrant"
        assert not (hold_dir / "decision.json").exists()

    def test_force_reprocess_deplace_vers_in_avec_nonce(self, tmp_path, monkeypatch):
        """FORCE_REPROCESS : le fichier est remis dans IN_DIR avec un suffixe nonce."""
        import app.main as orch

        _setup_dirs(tmp_path)
        self._patch_orch(orch, tmp_path, monkeypatch)

        job_key = "forcereproc__9999"
        hold_dir = tmp_path / "hold" / "duplicates" / job_key
        hold_dir.mkdir(parents=True)

        incoming_cbz = hold_dir / "20260101-120000__comic.cbz"
        incoming_cbz.write_bytes(b"fake cbz force")

        nonce = "deadbeef12345678"
        (hold_dir / "decision.json").write_text(
            json.dumps({"action": "FORCE_REPROCESS", "nonce": nonce}),
            encoding="utf-8",
        )

        index = {"jobs": {job_key: {"jobKey": job_key, "state": "DONE"}}}
        index_path = str(tmp_path / "index" / "jobs.json")

        orch.check_duplicate_decisions(index, index_path)

        in_files = list((tmp_path / "in").iterdir())
        assert len(in_files) == 1, "FORCE_REPROCESS doit remettre le fichier dans in/"
        # Le nom doit contenir le nonce (8 premiers caractères)
        assert "force-deadbeef" in in_files[0].name, "Le nom doit contenir le nonce"
        assert not incoming_cbz.exists()

    def test_force_reprocess_sans_nonce_genere_nonce_auto(self, tmp_path, monkeypatch):
        """FORCE_REPROCESS sans nonce dans la décision génère un nonce automatique."""
        import app.main as orch

        _setup_dirs(tmp_path)
        self._patch_orch(orch, tmp_path, monkeypatch)

        job_key = "forcenonce__auto"
        hold_dir = tmp_path / "hold" / "duplicates" / job_key
        hold_dir.mkdir(parents=True)

        incoming_cbz = hold_dir / "20260101-120000__comic.cbz"
        incoming_cbz.write_bytes(b"cbz sans nonce")

        # Décision FORCE_REPROCESS sans nonce
        (hold_dir / "decision.json").write_text(
            json.dumps({"action": "FORCE_REPROCESS"}),
            encoding="utf-8",
        )

        index = {"jobs": {job_key: {"jobKey": job_key, "state": "DONE"}}}
        index_path = str(tmp_path / "index" / "jobs.json")

        orch.check_duplicate_decisions(index, index_path)

        in_files = list((tmp_path / "in").iterdir())
        assert len(in_files) == 1, "FORCE_REPROCESS sans nonce doit quand même remettre le fichier"
        # Le nom doit contenir "force-" suivi d'un hash auto
        assert "force-" in in_files[0].name

    def test_hold_sans_decision_reste_intouche(self, tmp_path, monkeypatch):
        """Un dossier hold sans decision.json ne doit pas être traité."""
        import app.main as orch

        _setup_dirs(tmp_path)
        self._patch_orch(orch, tmp_path, monkeypatch)

        job_key = "pending__nodecision"
        hold_dir = tmp_path / "hold" / "duplicates" / job_key
        hold_dir.mkdir(parents=True)

        incoming_cbz = hold_dir / "20260101-120000__comic.cbz"
        incoming_cbz.write_bytes(b"en attente")

        index = {"jobs": {}}
        index_path = str(tmp_path / "index" / "jobs.json")

        orch.check_duplicate_decisions(index, index_path)

        # Fichier intact, rien ne doit avoir bougé
        assert incoming_cbz.exists(), "Sans decision.json, le fichier doit rester intact"


# ---------------------------------------------------------------------------
# process_tick — flux complet (P0-ORCH-01)
# ---------------------------------------------------------------------------

class TestProcessTickFlux:
    """Tests du flux complet de process_tick via mocks HTTP."""

    def _patch_all(self, orch, tmp_path, monkeypatch):
        """Patch tous les répertoires globaux de l'orchestrateur."""
        monkeypatch.setattr(orch, "IN_DIR", str(tmp_path / "in"))
        monkeypatch.setattr(orch, "WORK_DIR", str(tmp_path / "work"))
        monkeypatch.setattr(orch, "OUT_DIR", str(tmp_path / "out"))
        monkeypatch.setattr(orch, "ERROR_DIR", str(tmp_path / "error"))
        monkeypatch.setattr(orch, "ARCHIVE_DIR", str(tmp_path / "archive"))
        monkeypatch.setattr(orch, "HOLD_DUP_DIR", str(tmp_path / "hold" / "duplicates"))
        monkeypatch.setattr(orch, "DUP_REPORTS_DIR", str(tmp_path / "reports" / "duplicates"))
        monkeypatch.setattr(orch, "INDEX_DIR", str(tmp_path / "index"))

    def test_decouverte_fichier_valide_cree_job_discovered(self, tmp_path, monkeypatch):
        """Un fichier CBZ valide dans in/ est découvert, soumis à PREP et passe en PREP_RUNNING."""
        import app.main as orch
        from unittest.mock import patch as _patch

        _setup_dirs(tmp_path)
        self._patch_all(orch, tmp_path, monkeypatch)

        # Créer un CBZ avec signature ZIP valide
        cbz_file = tmp_path / "in" / "test.cbz"
        cbz_file.write_bytes(_make_zip_header())

        config = _make_config(tmp_path)
        monkeypatch.setattr(orch, "check_disk_space", lambda *a, **kw: True)

        in_flight = {}
        index = {"jobs": {}}
        index_path = str(tmp_path / "index" / "jobs.json")
        profile = {"ocr": {"lang": "fra+eng"}, "prep": {}}

        with _patch("app.main.submit_prep"):  # éviter la connexion réelle au service
            orch.process_tick(in_flight, index, index_path, profile, config)

        assert len(in_flight) == 1, "Le fichier doit être détecté et mis en in_flight"
        job_key = list(in_flight.keys())[0]
        assert in_flight[job_key]["stage"] == "PREP_RUNNING"
        assert job_key in index["jobs"]

    def test_decouverte_ignore_fichier_part(self, tmp_path, monkeypatch):
        """Un fichier .part dans in/ est ignoré à la découverte."""
        import app.main as orch

        _setup_dirs(tmp_path)
        self._patch_all(orch, tmp_path, monkeypatch)

        # Fichier .part (téléchargement en cours) — doit être ignoré
        (tmp_path / "in" / "test.cbz.part").write_bytes(_make_zip_header())

        config = _make_config(tmp_path)
        in_flight = {}
        index = {"jobs": {}}
        index_path = str(tmp_path / "index" / "jobs.json")
        profile = {}

        orch.process_tick(in_flight, index, index_path, profile, config)

        assert len(in_flight) == 0, "Les fichiers .part ne doivent pas être découverts"

    def test_fichier_trop_grand_rejete_et_metrique_incrementee(self, tmp_path, monkeypatch):
        """Un fichier dépassant MAX_INPUT_SIZE_MB est rejeté avec métrique input_rejected_size."""
        import app.main as orch

        _setup_dirs(tmp_path)
        self._patch_all(orch, tmp_path, monkeypatch)

        cbz_file = tmp_path / "in" / "huge.cbz"
        # 300 octets pour dépasser la limite de 0.0001 MB (~104 o) tout en gardant la signature ZIP valide
        cbz_file.write_bytes(_make_zip_header() + b"\x00" * 200)

        config = _make_config(tmp_path)
        # Simuler que le fichier dépasse la limite (max_input_size_mb = 0.0001 MB ~= 104 o)
        config["max_input_size_mb"] = 0.0001

        in_flight = {}
        index = {"jobs": {}}
        index_path = str(tmp_path / "index" / "jobs.json")
        profile = {}

        orch.process_tick(in_flight, index, index_path, profile, config)

        assert len(in_flight) == 0, "Le fichier trop grand ne doit pas être mis en in_flight"
        assert config["metrics"]["input_rejected_size"] == 1

        # Le fichier doit être dans error/
        error_files = list((tmp_path / "error").iterdir())
        assert len(error_files) == 1

    def test_fichier_signature_invalide_rejete(self, tmp_path, monkeypatch):
        """Un fichier avec une signature magic invalide est rejeté avec métrique input_rejected_signature."""
        import app.main as orch

        _setup_dirs(tmp_path)
        self._patch_all(orch, tmp_path, monkeypatch)

        # Fichier avec une fausse signature (pas ZIP ni RAR)
        bad_file = tmp_path / "in" / "malicious.cbz"
        bad_file.write_bytes(b"\x00\x00\x00\x00" + b"not a zip" * 10)

        config = _make_config(tmp_path)
        monkeypatch.setattr(orch, "check_disk_space", lambda *a, **kw: True)

        in_flight = {}
        index = {"jobs": {}}
        index_path = str(tmp_path / "index" / "jobs.json")
        profile = {}

        orch.process_tick(in_flight, index, index_path, profile, config)

        assert len(in_flight) == 0
        assert config["metrics"]["input_rejected_signature"] == 1
        error_files = list((tmp_path / "error").iterdir())
        assert len(error_files) == 1

    def test_fichier_doublon_cree_rapport_hold(self, tmp_path, monkeypatch):
        """Un fichier avec un jobKey déjà dans l'index crée un rapport de doublon."""
        import app.main as orch

        _setup_dirs(tmp_path)
        self._patch_all(orch, tmp_path, monkeypatch)

        cbz_file = tmp_path / "in" / "comic.cbz"
        cbz_file.write_bytes(_make_zip_header())

        # Pré-remplir le profile pour contrôler le jobKey
        monkeypatch.setattr(orch, "check_disk_space", lambda *a, **kw: True)
        monkeypatch.setattr(orch, "sha256_file", lambda *a, **kw: "filehash001")

        from unittest.mock import patch as _patch
        with _patch("app.main.make_job_key", return_value=("profilehash", "filehash001__profilehash")):
            job_key = "filehash001__profilehash"
            config = _make_config(tmp_path)
            in_flight = {}
            index = {"jobs": {job_key: {"jobKey": job_key, "state": "DONE", "outPdf": "/out/x.pdf"}}}
            index_path = str(tmp_path / "index" / "jobs.json")
            profile = {}

            orch.process_tick(in_flight, index, index_path, profile, config)

        assert len(in_flight) == 0, "Un doublon ne doit pas entrer dans in_flight"
        # Rapport de doublon créé
        reports = list((tmp_path / "reports" / "duplicates").iterdir())
        assert len(reports) == 1

    def test_prep_running_poll_done_passe_en_ocr_running(self, tmp_path, monkeypatch):
        """Quand PREP répond DONE, le job passe en PREP_DONE puis est soumis à OCR (OCR_RUNNING)."""
        import app.main as orch
        from unittest.mock import patch as _patch, MagicMock

        _setup_dirs(tmp_path)
        self._patch_all(orch, tmp_path, monkeypatch)

        job_key = "prepdonejob__001"
        job_dir_path = tmp_path / "work" / job_key
        job_dir_path.mkdir(parents=True)
        raw_pdf = str(job_dir_path / "raw.pdf")
        (job_dir_path / "state.json").write_text(
            json.dumps({"jobKey": job_key, "state": "PREP_RUNNING"})
        )

        config = _make_config(tmp_path)
        in_flight = {
            job_key: {
                "stage": "PREP_RUNNING",
                "inputName": "comic.cbz",
                "inputPath": str(job_dir_path / "comic.cbz"),
                "attemptPrep": 1,
                "attemptOcr": 0,
            }
        }
        index = {"jobs": {job_key: {"jobKey": job_key, "state": "PREP_RUNNING"}}}
        index_path = str(tmp_path / "index" / "jobs.json")

        # PREP poll retourne DONE ; OCR poll retourne RUNNING (même tick, étapes distinctes)
        def _poll_side_effect(url, jk):
            if "prep" in url:
                return {"state": "DONE", "artifacts": {"rawPdf": raw_pdf}}
            return {"state": "RUNNING"}

        mock_poll = MagicMock(side_effect=_poll_side_effect)
        mock_submit_ocr = MagicMock()  # succès silencieux

        with _patch("app.main.poll_job", mock_poll):
            with _patch("app.main.submit_ocr", mock_submit_ocr):
                with _patch("app.main.check_duplicate_decisions"):
                    with _patch("app.main.discover_inputs", return_value=iter([])):
                        orch.process_tick(in_flight, index, index_path, {}, config)

        assert in_flight[job_key]["stage"] == "OCR_RUNNING"
        assert in_flight[job_key]["rawPdf"] == raw_pdf

    def test_prep_running_poll_error_passe_a_prep_retry(self, tmp_path, monkeypatch):
        """Quand PREP répond ERROR, le job passe en PREP_RETRY."""
        import app.main as orch
        from unittest.mock import patch as _patch, MagicMock

        _setup_dirs(tmp_path)
        self._patch_all(orch, tmp_path, monkeypatch)

        job_key = "prepartry__002"
        job_dir_path = tmp_path / "work" / job_key
        job_dir_path.mkdir(parents=True)
        (job_dir_path / "state.json").write_text(
            json.dumps({"jobKey": job_key, "state": "PREP_RUNNING"})
        )

        config = _make_config(tmp_path)
        in_flight = {
            job_key: {
                "stage": "PREP_RUNNING",
                "inputName": "comic.cbz",
                "inputPath": str(job_dir_path / "comic.cbz"),
                "attemptPrep": 1,
                "attemptOcr": 0,
            }
        }
        index = {"jobs": {job_key: {"jobKey": job_key}}}
        index_path = str(tmp_path / "index" / "jobs.json")

        mock_poll = MagicMock(return_value={"state": "ERROR", "message": "7z failed"})

        with _patch("app.main.poll_job", mock_poll):
            with _patch("app.main.check_duplicate_decisions"):
                with _patch("app.main.discover_inputs", return_value=iter([])):
                    orch.process_tick(in_flight, index, index_path, {}, config)

        assert in_flight[job_key]["stage"] == "PREP_RETRY"

    def test_ocr_done_valide_cree_pdf_dans_out(self, tmp_path, monkeypatch):
        """Quand OCR répond DONE et le PDF est valide, le job est finalisé dans out/."""
        import app.main as orch
        from unittest.mock import patch as _patch, MagicMock

        _setup_dirs(tmp_path)
        self._patch_all(orch, tmp_path, monkeypatch)

        job_key = "ocrdonejob__001"
        job_dir_path = tmp_path / "work" / job_key
        job_dir_path.mkdir(parents=True)

        # Créer un final.pdf valide (header %PDF- + taille OK)
        final_pdf = job_dir_path / "final.pdf"
        final_pdf.write_bytes(b"%PDF-1.4 " + b"x" * 2000)

        # Fichier source dans work dir
        input_cbz = job_dir_path / "comic.cbz"
        input_cbz.write_bytes(b"fake cbz")

        (job_dir_path / "state.json").write_text(
            json.dumps({"jobKey": job_key, "state": "OCR_RUNNING"})
        )

        config = _make_config(tmp_path)
        config["min_pdf_size_bytes"] = 100
        in_flight = {
            job_key: {
                "stage": "OCR_RUNNING",
                "inputName": "comic.cbz",
                "inputPath": str(input_cbz),
                "attemptPrep": 1,
                "attemptOcr": 1,
                "rawPdf": str(job_dir_path / "raw.pdf"),
            }
        }
        index = {"jobs": {job_key: {"jobKey": job_key, "state": "OCR_RUNNING"}}}
        index_path = str(tmp_path / "index" / "jobs.json")

        mock_poll = MagicMock(return_value={"state": "DONE", "artifacts": {"finalPdf": str(final_pdf)}})

        with _patch("app.main.poll_job", mock_poll):
            with _patch("app.main.check_duplicate_decisions"):
                with _patch("app.main.discover_inputs", return_value=iter([])):
                    orch.process_tick(in_flight, index, index_path, {}, config)

        # Le job ne doit plus être en in_flight (supprimé après DONE)
        assert job_key not in in_flight, "Le job doit être retiré de in_flight après DONE"
        # Le PDF doit être dans out/
        out_files = list((tmp_path / "out").glob("*.pdf"))
        assert len(out_files) == 1
        assert "__job-" in out_files[0].name
        assert config["metrics"]["done"] == 1

    def test_ocr_done_pdf_invalide_passe_en_retry(self, tmp_path, monkeypatch):
        """Quand OCR répond DONE mais le PDF est invalide, le job bascule en OCR_RETRY."""
        import app.main as orch
        from unittest.mock import patch as _patch, MagicMock

        _setup_dirs(tmp_path)
        self._patch_all(orch, tmp_path, monkeypatch)

        job_key = "badpdf__001"
        job_dir_path = tmp_path / "work" / job_key
        job_dir_path.mkdir(parents=True)

        # PDF invalide : trop petit (< min_pdf_size_bytes)
        final_pdf = job_dir_path / "final.pdf"
        final_pdf.write_bytes(b"%PDF-" + b"x" * 10)

        (job_dir_path / "state.json").write_text(
            json.dumps({"jobKey": job_key, "state": "OCR_RUNNING"})
        )

        config = _make_config(tmp_path)
        config["min_pdf_size_bytes"] = 1024  # exige au moins 1 Ko
        in_flight = {
            job_key: {
                "stage": "OCR_RUNNING",
                "inputName": "comic.cbz",
                "inputPath": str(job_dir_path / "comic.cbz"),
                "attemptPrep": 1,
                "attemptOcr": 1,
                "rawPdf": str(job_dir_path / "raw.pdf"),
            }
        }
        index = {"jobs": {job_key: {"jobKey": job_key}}}
        index_path = str(tmp_path / "index" / "jobs.json")

        mock_poll = MagicMock(return_value={"state": "DONE", "artifacts": {"finalPdf": str(final_pdf)}})

        with _patch("app.main.poll_job", mock_poll):
            with _patch("app.main.check_duplicate_decisions"):
                with _patch("app.main.discover_inputs", return_value=iter([])):
                    orch.process_tick(in_flight, index, index_path, {}, config)

        assert in_flight[job_key]["stage"] == "OCR_RETRY", "PDF invalide → OCR_RETRY"
        assert config["metrics"]["pdf_invalid"] == 1

    def test_prep_max_attempts_passe_en_error(self, tmp_path, monkeypatch):
        """Un job ayant atteint MAX_ATTEMPTS_PREP bascule directement en ERROR."""
        import app.main as orch
        from unittest.mock import patch as _patch

        _setup_dirs(tmp_path)
        self._patch_all(orch, tmp_path, monkeypatch)

        job_key = "maxprep__001"
        job_dir_path = tmp_path / "work" / job_key
        job_dir_path.mkdir(parents=True)

        input_cbz = job_dir_path / "comic.cbz"
        input_cbz.write_bytes(b"fake")

        (job_dir_path / "state.json").write_text(
            json.dumps({"jobKey": job_key, "state": "PREP_RETRY"})
        )

        config = _make_config(tmp_path)
        config["max_attempts_prep"] = 3
        in_flight = {
            job_key: {
                "stage": "DISCOVERED",
                "inputName": "comic.cbz",
                "inputPath": str(input_cbz),
                "attemptPrep": 3,  # déjà au maximum
                "attemptOcr": 0,
            }
        }
        index = {"jobs": {job_key: {"jobKey": job_key}}}
        index_path = str(tmp_path / "index" / "jobs.json")

        with _patch("app.main.check_duplicate_decisions"):
            with _patch("app.main.discover_inputs", return_value=iter([])):
                orch.process_tick(in_flight, index, index_path, {}, config)

        assert job_key not in in_flight, "Après max attempts, le job doit quitter in_flight"
        assert index["jobs"][job_key]["state"] == "ERROR_PREP"
        assert config["metrics"]["error"] == 1

