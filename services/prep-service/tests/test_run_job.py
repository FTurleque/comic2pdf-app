"""
Tests de run_job, worker_loop, startup/shutdown — prep-service.
subprocess.run est mocké — aucun outil externe requis.

Cibles de patch :
  app.main.subprocess.run       (import subprocess en ligne 6 de main.py)
  app.main.list_and_sort_images (from app.core import … en ligne 13)
  app.main.images_to_pdf        (idem)
  app.main.time.sleep           (import time en ligne 8)
  app.main.threading.Thread     (import threading en ligne 7)

Note : les patches ciblent le module app.main via son objet direct (importé en tant que _m)
pour garantir que le bon espace de noms est patché quel que soit l'ordre des imports.
"""
import json
import os
import sys
import threading
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from app.utils import atomic_write_json, ensure_dir, now_iso
import app.main as _m
# Note : _m est importé pour initialiser l'objet module au premier import.
# Les tests utilisent _get_m() pour obtenir le module courant (voir ci-dessous).


def _get_m():
    """
    Retourne le module app.main courant depuis sys.modules.
    Nécessaire car test_api.py recharge app.main via 'del sys.modules["app.main"]'
    dans sa fixture data_dir — ce qui rend l'import au niveau module obsolète.
    """
    import sys
    import importlib
    return sys.modules.get("app.main") or importlib.import_module("app.main")


# ---------------------------------------------------------------------------
# Fixture autouse : garantit que l'état global de app.main est propre entre tests
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _reset_app_main_state():
    """
    Remet _stop_event et _worker_threads à l'état initial avant et après chaque test.
    Nécessaire car test_api.py et TestClient déclenchent startup()/shutdown() qui
    modifient ces globals partagés. On cible le module courant via _get_m() car
    test_api.py peut recharger app.main (del sys.modules["app.main"]).
    """
    m = _get_m()
    m._stop_event.clear()
    m._worker_threads.clear()
    yield
    m2 = _get_m()
    m2._stop_event.set()   # Arrêter tout éventuel thread lancé dans le test
    m2._worker_threads.clear()
    m2._stop_event.clear()  # État propre pour le test suivant


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_meta(tmp_path, job_id="job-test"):
    """Crée un fichier meta JSON minimal dans running/ et retourne (meta_path, work_dir)."""
    work_dir = str(tmp_path / "work")
    ensure_dir(work_dir)
    running_dir = str(tmp_path / "running")
    ensure_dir(running_dir)
    input_cbz = str(tmp_path / f"{job_id}.cbz")
    with open(input_cbz, "wb") as f:
        f.write(b"PK\x03\x04")
    meta = {
        "jobId": job_id,
        "inputPath": input_cbz,
        "workDir": work_dir,
        "state": "QUEUED",
        "updatedAt": now_iso(),
    }
    meta_path = os.path.join(running_dir, f"{job_id}.json")
    atomic_write_json(meta_path, meta)
    return meta_path, work_dir


def _proc(rc=0):
    """Retourne un mock de subprocess.CompletedProcess."""
    m = MagicMock()
    m.returncode = rc
    m.stdout = "output"
    m.stderr = ""
    return m


def _fake_img2pdf(images, dest_path):
    """Mock de images_to_pdf : crée le fichier dest_path pour que os.replace réussisse."""
    with open(dest_path, "wb") as f:
        f.write(b"%PDF-fake")


# ---------------------------------------------------------------------------
# Tests run_job
# ---------------------------------------------------------------------------

class TestRunJob:
    """Tests de la fonction run_job."""

    def test_happy_path_etat_done(self, tmp_path):
        """run_job happy path : extraction OK + images trouvées → état DONE + raw.pdf créé."""
        m = _get_m()
        meta_path, work_dir = _make_meta(tmp_path, "jh")
        with patch.object(m, "subprocess") as mock_sub, \
             patch.object(m, "list_and_sort_images", return_value=["img1.jpg", "img2.jpg"]), \
             patch.object(m, "images_to_pdf", side_effect=_fake_img2pdf):
            mock_sub.run.return_value = _proc(0)
            m.run_job(meta_path)

        state = json.loads(open(meta_path).read())
        assert state["state"] == "DONE"
        assert state["message"] == "raw.pdf ready"
        assert "rawPdf" in state["artifacts"]
        raw_pdf = os.path.join(work_dir, "jh", "raw.pdf")
        assert os.path.exists(raw_pdf)

    def test_meta_absent_retourne_silencieusement(self, tmp_path):
        """run_job avec fichier meta absent retourne None sans lever d'exception."""
        m = _get_m()
        result = m.run_job(str(tmp_path / "absent.json"))
        assert result is None

    def test_7z_fail_etat_error(self, tmp_path):
        """run_job avec 7z returncode=1 → état ERROR + RuntimeError levée."""
        m = _get_m()
        meta_path, _ = _make_meta(tmp_path, "j7z")
        with patch.object(m, "subprocess") as mock_sub, \
             pytest.raises(RuntimeError, match="7z failed"):
            mock_sub.run.return_value = _proc(1)
            m.run_job(meta_path)

        state = json.loads(open(meta_path).read())
        assert state["state"] == "ERROR"
        assert "7z failed" in state["message"]
        assert state["error"]["type"] == "RuntimeError"

    def test_no_images_etat_error(self, tmp_path):
        """run_job avec liste images vide → état ERROR + RuntimeError 'no images'."""
        m = _get_m()
        meta_path, _ = _make_meta(tmp_path, "jni")
        with patch.object(m, "subprocess") as mock_sub, \
             patch.object(m, "list_and_sort_images", return_value=[]), \
             pytest.raises(RuntimeError, match="no images"):
            mock_sub.run.return_value = _proc(0)
            m.run_job(meta_path)

        state = json.loads(open(meta_path).read())
        assert state["state"] == "ERROR"
        assert "no images" in state["message"]

    def test_exception_generique_etat_error(self, tmp_path):
        """run_job avec exception inattendue → état ERROR + exception propagée."""
        m = _get_m()
        meta_path, _ = _make_meta(tmp_path, "jex")
        with patch.object(m, "subprocess") as mock_sub, \
             patch.object(m, "list_and_sort_images", side_effect=OSError("disk full")), \
             pytest.raises(OSError, match="disk full"):
            mock_sub.run.return_value = _proc(0)
            m.run_job(meta_path)

        state = json.loads(open(meta_path).read())
        assert state["state"] == "ERROR"
        assert "disk full" in state["message"]
        assert state["error"]["type"] == "OSError"

    def test_heartbeat_cree(self, tmp_path):
        """run_job crée un fichier prep.heartbeat dans le job_dir."""
        m = _get_m()
        meta_path, work_dir = _make_meta(tmp_path, "jhb")
        with patch.object(m, "subprocess") as mock_sub, \
             patch.object(m, "list_and_sort_images", return_value=["img.jpg"]), \
             patch.object(m, "images_to_pdf", side_effect=_fake_img2pdf):
            mock_sub.run.return_value = _proc(0)
            m.run_job(meta_path)

        hb = os.path.join(work_dir, "jhb", "prep.heartbeat")
        assert os.path.exists(hb)
        assert len(open(hb).read()) > 0

    def test_subprocess_appele_avec_7z_x(self, tmp_path):
        """run_job appelle subprocess.run avec la commande '7z x ...'."""
        m = _get_m()
        meta_path, _ = _make_meta(tmp_path, "jcmd")
        with patch.object(m, "subprocess") as mock_sub, \
             patch.object(m, "list_and_sort_images", return_value=["img.jpg"]), \
             patch.object(m, "images_to_pdf", side_effect=_fake_img2pdf):
            mock_sub.run.return_value = _proc(0)
            m.run_job(meta_path)

        assert mock_sub.run.called
        cmd_args = mock_sub.run.call_args[0][0]
        assert cmd_args[0] == "7z"
        assert cmd_args[1] == "x"

    def test_etat_running_avant_subprocess(self, tmp_path):
        """update_state RUNNING est appelé avant subprocess.run."""
        m = _get_m()
        meta_path, _ = _make_meta(tmp_path, "jrun")
        states_seen = []

        def fake_run(cmd, **kwargs):
            state = json.loads(open(meta_path).read())
            states_seen.append(state["state"])
            return _proc(0)

        with patch.object(m, "subprocess") as mock_sub, \
             patch.object(m, "list_and_sort_images", return_value=[]), \
             pytest.raises(RuntimeError):
            mock_sub.run.side_effect = fake_run
            m.run_job(meta_path)

        assert "RUNNING" in states_seen

    def test_pages_dir_reconstruit_avant_extraction(self, tmp_path):
        """run_job recrée pages_dir proprement avant l'extraction 7z."""
        m = _get_m()
        meta_path, work_dir = _make_meta(tmp_path, "jpages")
        pages_dir = os.path.join(work_dir, "jpages", "pages")
        os.makedirs(pages_dir, exist_ok=True)
        open(os.path.join(pages_dir, "old.txt"), "w").close()

        with patch.object(m, "subprocess") as mock_sub, \
             patch.object(m, "list_and_sort_images", return_value=[]), \
             pytest.raises(RuntimeError, match="no images"):
            mock_sub.run.return_value = _proc(0)
            m.run_job(meta_path)

        assert os.path.isdir(pages_dir)
        assert not os.path.exists(os.path.join(pages_dir, "old.txt"))


# ---------------------------------------------------------------------------
# Tests worker_loop
# ---------------------------------------------------------------------------

class TestWorkerLoop:
    """Tests de la boucle worker_loop."""

    def _setup(self, tmp_path, monkeypatch, suffix=""):
        """Crée et patche les répertoires nécessaires au worker."""
        m = _get_m()
        dirs = {
            "queue":   tmp_path / f"wq{suffix}",
            "running": tmp_path / f"wr{suffix}",
            "done":    tmp_path / f"wd{suffix}",
            "error":   tmp_path / f"we{suffix}",
        }
        for d in dirs.values():
            d.mkdir()
        monkeypatch.setattr(m, "QUEUE_DIR",   str(dirs["queue"]))
        monkeypatch.setattr(m, "RUNNING_DIR", str(dirs["running"]))
        monkeypatch.setattr(m, "DONE_DIR",    str(dirs["done"]))
        monkeypatch.setattr(m, "ERROR_DIR",   str(dirs["error"]))
        return dirs, m

    def test_job_deplace_vers_done(self, tmp_path, monkeypatch):
        """worker_loop traite un job et le déplace vers DONE_DIR."""
        dirs, m = self._setup(tmp_path, monkeypatch, "1")
        (dirs["queue"] / "j1.json").write_text('{"jobId":"j1","state":"QUEUED"}')
        stop = threading.Event()

        def fake_run_job(meta_path):
            stop.set()  # Signaler l'arrêt après traitement

        with patch.object(m, "run_job", side_effect=fake_run_job):
            t = threading.Thread(target=m.worker_loop, args=(stop,), daemon=True)
            t.start()
            t.join(timeout=3)

        assert not t.is_alive(), "worker_loop doit s'être arrêté"
        assert (dirs["done"] / "j1.json").exists(), "job doit être dans DONE_DIR"

    def test_job_erreur_deplace_vers_error(self, tmp_path, monkeypatch):
        """worker_loop déplace le job vers ERROR_DIR si run_job lève une exception."""
        dirs, m = self._setup(tmp_path, monkeypatch, "2")
        (dirs["queue"] / "j2.json").write_text('{"jobId":"j2","state":"QUEUED"}')
        stop = threading.Event()

        def fake_run_fail(meta_path):
            stop.set()
            raise RuntimeError("boom")

        with patch.object(m, "run_job", side_effect=fake_run_fail):
            t = threading.Thread(target=m.worker_loop, args=(stop,), daemon=True)
            t.start()
            t.join(timeout=3)

        assert not t.is_alive()
        assert (dirs["error"] / "j2.json").exists(), "job doit être dans ERROR_DIR"

    def test_queue_vide_sleep_puis_arret(self, tmp_path, monkeypatch):
        """worker_loop sans job disponible appelle time.sleep, s'arrête via stop_event."""
        _, m = self._setup(tmp_path, monkeypatch, "3")
        stop = threading.Event()

        def fake_sleep(t):
            stop.set()  # Arrêter au premier sleep

        with patch.object(m, "time") as mock_time:
            mock_time.sleep.side_effect = fake_sleep
            t = threading.Thread(target=m.worker_loop, args=(stop,), daemon=True)
            t.start()
            t.join(timeout=3)

        assert not t.is_alive()


# ---------------------------------------------------------------------------
# Tests startup / shutdown
# ---------------------------------------------------------------------------

class TestStartupShutdown:
    """Tests des handlers FastAPI startup et shutdown."""

    def test_startup_disable_workers_pas_de_thread(self, tmp_path, monkeypatch):
        """startup() avec DISABLE_WORKERS=1 ne lance aucun thread worker."""
        m = _get_m()
        monkeypatch.setenv("DISABLE_WORKERS", "1")
        q = tmp_path / "q_su1"
        r = tmp_path / "r_su1"
        q.mkdir(); r.mkdir()
        monkeypatch.setattr(m, "QUEUE_DIR",   str(q))
        monkeypatch.setattr(m, "RUNNING_DIR", str(r))

        m.startup()

        assert len(m._worker_threads) == 0

    def test_startup_lance_threads_quand_actif(self, tmp_path, monkeypatch):
        """startup() avec DISABLE_WORKERS=0 lance SERVICE_CONCURRENCY threads."""
        m = _get_m()
        monkeypatch.setenv("DISABLE_WORKERS", "0")
        monkeypatch.setattr(m, "SERVICE_CONCURRENCY", 1)
        q = tmp_path / "q_su2"
        r = tmp_path / "r_su2"
        q.mkdir(); r.mkdir()
        monkeypatch.setattr(m, "QUEUE_DIR",   str(q))
        monkeypatch.setattr(m, "RUNNING_DIR", str(r))

        launched = []
        original_thread = threading.Thread

        def fake_thread(*args, **kwargs):
            t = original_thread(*args, **kwargs)
            launched.append(t)
            return t

        with patch.object(m, "threading") as mock_threading:
            mock_threading.Thread.side_effect = fake_thread
            mock_threading.Event = threading.Event
            m.startup()

        m._stop_event.set()
        for t in launched:
            t.join(timeout=1)

        assert len(launched) >= 1

    def test_shutdown_set_stop_event(self):
        """shutdown() met _stop_event pour signaler l'arrêt des workers."""
        m = _get_m()
        assert not m._stop_event.is_set()

        m.shutdown()

        assert m._stop_event.is_set()



