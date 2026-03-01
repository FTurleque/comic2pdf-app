"""
Tests de concurrence de l'orchestrateur.

Scénario : 10 faux CBZ (signature ZIP + contenu unique => SHA-256 distincts)
déposés dans /in. HTTP PREP/OCR entièrement mocké (FakeServiceRouter stateful).
Pilotage déterministe : boucle de 60 ticks max sur process_tick() (pas de sleep).

Configuration forcée :
  MAX_JOBS_IN_FLIGHT=3, PREP_CONCURRENCY=2, OCR_CONCURRENCY=1.

Assertions :
  1. PREP_RUNNING <= 2 à chaque tick.
  2. OCR_RUNNING  <= 1 à chaque tick.
  3. in_flight total <= 3 à chaque tick.
  4. 10 jobs DONE dans l'index + 0 job en vol après la boucle.
  5. /out contient exactement 10 PDF (convention __job-<jobKey>.pdf).

Aucun outil externe requis.
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ---------------------------------------------------------------------------
# Constantes de test
# ---------------------------------------------------------------------------

PREP_URL        = "http://mock-prep:8080"
OCR_URL         = "http://mock-ocr:8080"
PREP_MATURATION = 2   # ticks avant PREP DONE
OCR_MATURATION  = 2   # ticks avant OCR DONE
MAX_TICKS       = 60
NB_JOBS         = 10

# Profil canonique fixe et déterministe (SHA-256 stable)
_PROFILE = {
    "ocr": {
        "lang": "eng+fra",
        "rotatePages": True,
        "deskew": True,
        "optimize": 1,
        "tools": {"ocrmypdf": "14.0.0", "tesseract": "5.0.0"},
    },
    "prep": {"tools": {"img2pdf": "0.4.4", "p7zip": "21.07"}},
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _setup_dirs(tmp_path):
    """Crée l'arborescence de données minimale."""
    for d in ["in", "out", "work", "error", "archive",
              "hold/duplicates", "reports/duplicates", "index"]:
        (tmp_path / d).mkdir(parents=True, exist_ok=True)


def _patch_orch(monkeypatch, orch, tmp_path):
    """Redirige tous les répertoires globaux de l'orchestrateur vers tmp_path."""
    monkeypatch.setattr(orch, "IN_DIR",          str(tmp_path / "in"))
    monkeypatch.setattr(orch, "WORK_DIR",        str(tmp_path / "work"))
    monkeypatch.setattr(orch, "OUT_DIR",         str(tmp_path / "out"))
    monkeypatch.setattr(orch, "ERROR_DIR",       str(tmp_path / "error"))
    monkeypatch.setattr(orch, "ARCHIVE_DIR",     str(tmp_path / "archive"))
    monkeypatch.setattr(orch, "HOLD_DUP_DIR",    str(tmp_path / "hold" / "duplicates"))
    monkeypatch.setattr(orch, "DUP_REPORTS_DIR", str(tmp_path / "reports" / "duplicates"))
    monkeypatch.setattr(orch, "INDEX_DIR",       str(tmp_path / "index"))


def _make_config(tmp_path) -> dict:
    """Config avec les limites de concurrence cibles."""
    return {
        "prep_url":           PREP_URL,
        "ocr_url":            OCR_URL,
        "work_dir":           str(tmp_path / "work"),
        "max_jobs_in_flight": 3,
        "prep_concurrency":   2,
        "ocr_concurrency":    1,
        "max_attempts_prep":  3,
        "max_attempts_ocr":   3,
        "job_timeout_s":      600,
        "index_dir":          str(tmp_path / "index"),
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
        "disk_free_factor":   2.0,
        "max_input_size_mb":  500,
    }


def _fake_cbz_bytes(i: int) -> bytes:
    """
    Faux fichier CBZ : magic ZIP + rembourrage unique par index.
    => check_file_signature passe (ZIP magic)
    => sha256 distinct par fichier => jobKey distinct
    """
    return b"PK\x03\x04" + b"\x00" * 22 + f"cbz_job_{i:04d}_unique_content".encode()


# ---------------------------------------------------------------------------
# Simulateur stateful HTTP (prep-service + ocr-service)
# ---------------------------------------------------------------------------

class FakeServiceRouter:
    """
    Simule prep-service et ocr-service sans réseau.

    Chaque job PREP/OCR attend PREP_MATURATION / OCR_MATURATION ticks avant DONE.
    - DONE PREP : crée raw.pdf valide sur disque (retourné dans artifacts).
    - DONE OCR  : crée final.pdf valide sur disque (>= 1024 bytes, header %PDF-).

    Enregistre des snapshots de concurrence après chaque tick.
    """

    def __init__(self, work_dir: str):
        self._work_dir = work_dir
        self._tick = 0
        self._prep_submitted: dict = {}
        self._ocr_submitted:  dict = {}
        self._prep_done: set = set()
        self._ocr_done:  set = set()
        self.snap_prep_running:   list = []
        self.snap_ocr_running:    list = []
        self.snap_total_inflight: list = []

    def advance_tick(self):
        """Incrémente le compteur de tick avant chaque appel à process_tick."""
        self._tick += 1

    def record_snapshot(self, in_flight: dict):
        """Enregistre les compteurs de concurrence instantanée après un tick."""
        n_prep  = sum(1 for m in in_flight.values() if m.get("stage") == "PREP_RUNNING")
        n_ocr   = sum(1 for m in in_flight.values() if m.get("stage") == "OCR_RUNNING")
        self.snap_prep_running.append(n_prep)
        self.snap_ocr_running.append(n_ocr)
        self.snap_total_inflight.append(len(in_flight))

    def submit_prep(self, job_key: str, _input_path: str):
        """Enregistre le tick de soumission PREP (input_path non utilisé dans le mock)."""
        self._prep_submitted[job_key] = self._tick

    def submit_ocr(self, job_key: str, _raw_pdf: str):
        """Enregistre le tick de soumission OCR (raw_pdf non utilisé dans le mock)."""
        self._ocr_submitted[job_key] = self._tick

    def poll_job(self, url: str, job_key: str) -> dict:
        """Délègue vers le bon simulateur selon l'URL."""
        if url == PREP_URL:
            return self._poll_prep(job_key)
        return self._poll_ocr(job_key)

    def _poll_prep(self, job_key: str) -> dict:
        if job_key not in self._prep_submitted:
            return {"state": "RUNNING"}
        age = self._tick - self._prep_submitted[job_key]
        if age >= PREP_MATURATION:
            if job_key not in self._prep_done:
                raw = os.path.join(self._work_dir, job_key, "raw.pdf")
                os.makedirs(os.path.dirname(raw), exist_ok=True)
                with open(raw, "wb") as f:
                    f.write(b"%PDF-1.4\n" + b"R" * 2048)
                self._prep_done.add(job_key)
            return {
                "state": "DONE",
                "artifacts": {
                    "rawPdf": os.path.join(self._work_dir, job_key, "raw.pdf")
                },
            }
        return {"state": "RUNNING"}

    def _poll_ocr(self, job_key: str) -> dict:
        if job_key not in self._ocr_submitted:
            return {"state": "RUNNING"}
        age = self._tick - self._ocr_submitted[job_key]
        if age >= OCR_MATURATION:
            if job_key not in self._ocr_done:
                final = os.path.join(self._work_dir, job_key, "final.pdf")
                os.makedirs(os.path.dirname(final), exist_ok=True)
                with open(final, "wb") as f:
                    f.write(b"%PDF-1.4\n" + b"0" * 2048)
                self._ocr_done.add(job_key)
            return {
                "state": "DONE",
                "artifacts": {
                    "finalPdf": os.path.join(self._work_dir, job_key, "final.pdf")
                },
            }
        return {"state": "RUNNING"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestConcurrence:
    """Tests de concurrence et de complétion du pipeline orchestrateur."""

    def test_10_jobs_pipeline_complet(self, tmp_path, monkeypatch):
        """
        10 faux CBZ valides → pipeline complet en <= 60 ticks.

        Vérifie à chaque tick :
          - PREP_RUNNING  <= PREP_CONCURRENCY  (2)
          - OCR_RUNNING   <= OCR_CONCURRENCY   (1)
          - in_flight     <= MAX_JOBS_IN_FLIGHT (3)

        Vérifie en fin :
          - 10 jobs DONE dans l'index
          - 0 job encore en vol
          - 10 PDF dans /out
        """
        import app.main as orch

        _setup_dirs(tmp_path)
        _patch_orch(monkeypatch, orch, tmp_path)

        for i in range(NB_JOBS):
            (tmp_path / "in" / f"comic_{i:02d}.cbz").write_bytes(_fake_cbz_bytes(i))

        config     = _make_config(tmp_path)
        router     = FakeServiceRouter(str(tmp_path / "work"))
        index      = {"jobs": {}}
        index_path = str(tmp_path / "index" / "jobs.json")

        with open(index_path, "w", encoding="utf-8") as fh:
            json.dump(index, fh)

        monkeypatch.setattr(orch, "submit_prep", router.submit_prep)
        monkeypatch.setattr(orch, "submit_ocr",  router.submit_ocr)
        monkeypatch.setattr(orch, "poll_job",    router.poll_job)

        in_flight: dict = {}

        for tick_num in range(MAX_TICKS):
            router.advance_tick()
            orch.process_tick(in_flight, index, index_path, _PROFILE, config)
            router.record_snapshot(in_flight)

            n_prep  = sum(1 for m in in_flight.values() if m.get("stage") == "PREP_RUNNING")
            n_ocr   = sum(1 for m in in_flight.values() if m.get("stage") == "OCR_RUNNING")
            n_total = len(in_flight)

            assert n_prep  <= 2, (
                f"Tick {tick_num + 1}: PREP_RUNNING={n_prep} dépasse PREP_CONCURRENCY=2"
            )
            assert n_ocr   <= 1, (
                f"Tick {tick_num + 1}: OCR_RUNNING={n_ocr} dépasse OCR_CONCURRENCY=1"
            )
            assert n_total <= 3, (
                f"Tick {tick_num + 1}: in_flight={n_total} dépasse MAX_JOBS_IN_FLIGHT=3"
            )

            done_count = sum(
                1 for e in index["jobs"].values() if e.get("state") == "DONE"
            )
            if done_count == NB_JOBS and n_total == 0:
                break

        done_jobs = [k for k, e in index["jobs"].items() if e.get("state") == "DONE"]
        non_done  = [
            (k, e.get("state"), in_flight.get(k, {}).get("stage"))
            for k, e in index["jobs"].items()
            if e.get("state") != "DONE"
        ]
        assert len(done_jobs) == NB_JOBS, (
            f"Seulement {len(done_jobs)}/{NB_JOBS} jobs DONE après {MAX_TICKS} ticks.\n"
            f"Non-DONE : {non_done}"
        )
        assert len(in_flight) == 0, (
            f"Jobs toujours en vol : {[(k, m.get('stage')) for k, m in in_flight.items()]}"
        )

        out_pdfs = sorted((tmp_path / "out").glob("*.pdf"))
        assert len(out_pdfs) == NB_JOBS, (
            f"Attendu {NB_JOBS} PDF dans /out, trouvé {len(out_pdfs)} : "
            f"{[p.name for p in out_pdfs]}"
        )

        max_prep  = max(router.snap_prep_running,   default=0)
        max_ocr   = max(router.snap_ocr_running,    default=0)
        max_total = max(router.snap_total_inflight,  default=0)

        assert max_prep  <= 2, f"Pic PREP_RUNNING={max_prep} > 2 observé dans les snapshots"
        assert max_ocr   <= 1, f"Pic OCR_RUNNING={max_ocr} > 1 observé dans les snapshots"
        assert max_total <= 3, f"Pic in_flight total={max_total} > 3 observé dans les snapshots"

    def test_limites_concurrence_avec_jobs_lents(self, tmp_path, monkeypatch):
        """
        Vérifie que les limites de concurrence tiennent même avec des jobs
        dont la maturation prend 5 ticks (simulation de jobs lents).
        """
        import app.main as orch

        _setup_dirs(tmp_path)
        _patch_orch(monkeypatch, orch, tmp_path)

        nb = 6  # 6 jobs suffisent pour ce test
        for i in range(nb):
            (tmp_path / "in" / f"slow_{i:02d}.cbz").write_bytes(_fake_cbz_bytes(100 + i))

        config     = _make_config(tmp_path)
        index      = {"jobs": {}}
        index_path = str(tmp_path / "index" / "jobs.json")
        with open(index_path, "w", encoding="utf-8") as fh:
            json.dump(index, fh)

        class SlowRouter(FakeServiceRouter):
            """Simulateur avec maturation étendue à 5 ticks pour PREP et OCR."""

            def _poll_prep(self, job_key: str) -> dict:
                if job_key not in self._prep_submitted:
                    return {"state": "RUNNING"}
                age = self._tick - self._prep_submitted[job_key]
                if age >= 5:
                    if job_key not in self._prep_done:
                        raw = os.path.join(self._work_dir, job_key, "raw.pdf")
                        os.makedirs(os.path.dirname(raw), exist_ok=True)
                        with open(raw, "wb") as f:
                            f.write(b"%PDF-1.4\n" + b"R" * 2048)
                        self._prep_done.add(job_key)
                    return {
                        "state": "DONE",
                        "artifacts": {
                            "rawPdf": os.path.join(self._work_dir, job_key, "raw.pdf")
                        },
                    }
                return {"state": "RUNNING"}

            def _poll_ocr(self, job_key: str) -> dict:
                if job_key not in self._ocr_submitted:
                    return {"state": "RUNNING"}
                age = self._tick - self._ocr_submitted[job_key]
                if age >= 5:
                    if job_key not in self._ocr_done:
                        final = os.path.join(self._work_dir, job_key, "final.pdf")
                        os.makedirs(os.path.dirname(final), exist_ok=True)
                        with open(final, "wb") as f:
                            f.write(b"%PDF-1.4\n" + b"0" * 2048)
                        self._ocr_done.add(job_key)
                    return {
                        "state": "DONE",
                        "artifacts": {
                            "finalPdf": os.path.join(self._work_dir, job_key, "final.pdf")
                        },
                    }
                return {"state": "RUNNING"}

        router = SlowRouter(str(tmp_path / "work"))
        monkeypatch.setattr(orch, "submit_prep", router.submit_prep)
        monkeypatch.setattr(orch, "submit_ocr",  router.submit_ocr)
        monkeypatch.setattr(orch, "poll_job",    router.poll_job)

        in_flight: dict = {}

        for tick_num in range(MAX_TICKS):
            router.advance_tick()
            orch.process_tick(in_flight, index, index_path, _PROFILE, config)
            router.record_snapshot(in_flight)

            n_prep  = sum(1 for m in in_flight.values() if m.get("stage") == "PREP_RUNNING")
            n_ocr   = sum(1 for m in in_flight.values() if m.get("stage") == "OCR_RUNNING")
            n_total = len(in_flight)

            assert n_prep  <= 2, f"Tick {tick_num + 1}: PREP_RUNNING={n_prep} > 2"
            assert n_ocr   <= 1, f"Tick {tick_num + 1}: OCR_RUNNING={n_ocr} > 1"
            assert n_total <= 3, f"Tick {tick_num + 1}: in_flight={n_total} > 3"

            done_count = sum(1 for e in index["jobs"].values() if e.get("state") == "DONE")
            if done_count == nb and len(in_flight) == 0:
                break

        done_jobs = [k for k, e in index["jobs"].items() if e.get("state") == "DONE"]
        assert len(done_jobs) == nb, (
            f"Seulement {len(done_jobs)}/{nb} jobs DONE (jobs lents, {MAX_TICKS} ticks max)"
        )
        assert len(in_flight) == 0, f"Jobs encore en vol : {list(in_flight.keys())}"

