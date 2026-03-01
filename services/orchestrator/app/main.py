"""
Orchestrateur watch-folder comic2pdf.
Pipeline : découverte -> PREP -> OCR -> archivage.
Gère la déduplication, les retries (MAX_ATTEMPTS par étape),
la détection de heartbeats périmés et les métriques basiques.
"""
import os
import time
import shutil
import threading
import requests

from app.core import (
    canonical_profile,
    stable_json,
    sha256_str,
    make_job_key,
    is_heartbeat_stale,
    make_empty_metrics,
    update_metrics,
    write_metrics,
    safe_load_json,
)
from app.utils import (
    ensure_dir,
    atomic_write_json,
    read_json,
    sha256_file,
    now_iso,
    validate_pdf,
    check_disk_space,
    check_input_size,
    check_file_signature,
    cleanup_old_workdirs,
)
from app.logger import get_logger
from app.http_server import OrchestratorState, start_http_server

_log = get_logger("orchestrator")

# ---------------------------------------------------------------------------
# Configuration (variables d'environnement)
# ---------------------------------------------------------------------------

DATA_DIR = os.environ.get("DATA_DIR", "/data")
IN_DIR = os.path.join(DATA_DIR, "in")
OUT_DIR = os.path.join(DATA_DIR, "out")
WORK_DIR = os.path.join(DATA_DIR, "work")
ERROR_DIR = os.path.join(DATA_DIR, "error")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")
HOLD_DUP_DIR = os.path.join(DATA_DIR, "hold", "duplicates")
DUP_REPORTS_DIR = os.path.join(DATA_DIR, "reports", "duplicates")
INDEX_DIR = os.path.join(DATA_DIR, "index")

PREP_URL = os.environ.get("PREP_URL", "http://prep-service:8080")
OCR_URL = os.environ.get("OCR_URL", "http://ocr-service:8080")

POLL_INTERVAL_MS = int(os.environ.get("POLL_INTERVAL_MS", "1000"))
PREP_CONCURRENCY = int(os.environ.get("PREP_CONCURRENCY", "2"))
OCR_CONCURRENCY = int(os.environ.get("OCR_CONCURRENCY", "1"))
MAX_JOBS_IN_FLIGHT = int(os.environ.get("MAX_JOBS_IN_FLIGHT", "3"))
MAX_ATTEMPTS_PREP = int(os.environ.get("MAX_ATTEMPTS_PREP", "3"))
MAX_ATTEMPTS_OCR = int(os.environ.get("MAX_ATTEMPTS_OCR", "3"))
OCR_LANG = os.environ.get("OCR_LANG", "fra+eng")
JOB_TIMEOUT_SECONDS = int(os.environ.get("JOB_TIMEOUT_SECONDS", "600"))

# Robustesse FS (B)
KEEP_WORK_DIR_DAYS = int(os.environ.get("KEEP_WORK_DIR_DAYS", "7"))
MIN_PDF_SIZE_BYTES = int(os.environ.get("MIN_PDF_SIZE_BYTES", "1024"))
DISK_FREE_FACTOR = float(os.environ.get("DISK_FREE_FACTOR", "2.0"))

# Hardening entrée (E)
MAX_INPUT_SIZE_MB = float(os.environ.get("MAX_INPUT_SIZE_MB", "500"))

# Observabilité HTTP (C)
ORCHESTRATOR_HTTP_PORT = int(os.environ.get("ORCHESTRATOR_HTTP_PORT", "8080"))
ORCHESTRATOR_HTTP_BIND = os.environ.get("ORCHESTRATOR_HTTP_BIND", "0.0.0.0")

# ---------------------------------------------------------------------------
# Helpers filesystem
# ---------------------------------------------------------------------------

def ensure_layout():
    """Crée tous les répertoires de données nécessaires."""
    for d in [IN_DIR, OUT_DIR, WORK_DIR, ERROR_DIR, ARCHIVE_DIR,
              HOLD_DUP_DIR, DUP_REPORTS_DIR, INDEX_DIR]:
        ensure_dir(d)


def get_service_info(url: str) -> dict:
    """
    Récupère les informations d'un service (GET /info).

    :param url: URL de base du service.
    :return: Dict JSON retourné par /info, ou dict minimal en cas d'erreur.
    """
    try:
        return requests.get(url + "/info", timeout=5).json()
    except Exception:
        return {"service": url, "versions": {"unknown": "unknown"}}


def move_atomic(src: str, dst: str):
    """
    Déplace atomiquement ``src`` vers ``dst``, en créant les dossiers parents.

    :param src: Chemin source.
    :param dst: Chemin destination.
    """
    ensure_dir(os.path.dirname(dst))
    os.replace(src, dst)


def base_name(path: str) -> str:
    """Retourne le nom de fichier sans extension."""
    return os.path.splitext(os.path.basename(path))[0]


def job_dir(job_key: str) -> str:
    """Retourne le chemin du dossier de travail pour un jobKey donné."""
    return os.path.join(WORK_DIR, job_key)


def job_state_path(job_key: str) -> str:
    """Retourne le chemin du fichier state.json pour un jobKey donné."""
    return os.path.join(job_dir(job_key), "state.json")


def update_state(job_key: str, patch: dict):
    """
    Met à jour le fichier state.json d'un job.
    Utilise safe_load_json pour résister aux fichiers corrompus ou absents.

    :param job_key: Identifiant du job.
    :param patch: Champs à fusionner.
    """
    p = job_state_path(job_key)
    ok, data = safe_load_json(p)
    if not ok:
        data = {"jobKey": job_key}
    data.update(patch)
    data["updatedAt"] = now_iso()
    atomic_write_json(p, data)


def load_index():
    """
    Charge l'index des jobs depuis le disque.

    :return: Tuple ``(index_dict, index_path)``.
    """
    ensure_dir(INDEX_DIR)
    p = os.path.join(INDEX_DIR, "jobs.json")
    return (read_json(p) or {"jobs": {}}), p


def save_index(index, path):
    """Persiste l'index des jobs sur le disque."""
    atomic_write_json(path, index)


def output_path_for(input_name: str, job_key: str) -> str:
    """
    Construit le chemin de sortie du PDF final.
    Convention : ``<nom_sans_ext>__job-<jobKey>.pdf``.

    :param input_name: Nom du fichier d'entrée (avec extension).
    :param job_key: Clé du job.
    :return: Chemin absolu du PDF de sortie.
    """
    return os.path.join(OUT_DIR, f"{base_name(input_name)}__job-{job_key}.pdf")


def discover_inputs():
    """
    Générateur qui liste les fichiers .cbz/.cbr dans IN_DIR (ignore .part).

    :return: Générateur de chemins absolus.
    """
    for fn in os.listdir(IN_DIR):
        lfn = fn.lower()
        if not (lfn.endswith(".cbz") or lfn.endswith(".cbr")):
            continue
        yield os.path.join(IN_DIR, fn)


# ---------------------------------------------------------------------------
# Bootstrap — Reprise après redémarrage
# ---------------------------------------------------------------------------

def recover_running_jobs(index: dict, index_path: str, in_flight: dict, config: dict):
    """
    Reprend proprement les jobs interrompus lors d'un redémarrage de l'orchestrateur.

    Parcourt ``index["jobs"]`` (source de vérité) à la recherche des entrées en état
    ``PREP_RUNNING`` ou ``OCR_RUNNING``. Pour chacune :

    - Charge ``work/<jobKey>/state.json`` via ``safe_load_json`` pour récupérer
      les tentatives réelles (``attemptPrep`` / ``attemptOcr``) et le ``inputPath``.
    - Si ``state.json`` est absent ou corrompu : tentative = 1 (le run interrompu comptait),
      ``inputPath`` = fallback ``work/<jobKey>/<inputName>``.
    - Si le nombre de tentatives dépasse le maximum configuré : bascule en ERROR
      (code ``max_attempts_after_restart``) et persiste l'index.
    - Sinon : réinjecte dans ``in_flight`` avec le stage ``PREP_RETRY`` ou ``OCR_RETRY``
      afin que le scheduler reprenne sur le tick suivant.

    Ne scanne pas ``work/`` pour découvrir des jobs. Source de vérité = ``index["jobs"]``.

    :param index: Index des jobs (modifié en place).
    :param index_path: Chemin du fichier index pour persistance.
    :param in_flight: Dict des jobs en vol (modifié en place).
    :param config: Dict de configuration (``max_attempts_prep``, ``max_attempts_ocr``,
                   ``work_dir``).
    """
    max_prep = config.get("max_attempts_prep", MAX_ATTEMPTS_PREP)
    max_ocr = config.get("max_attempts_ocr", MAX_ATTEMPTS_OCR)
    work_dir = config.get("work_dir", WORK_DIR)
    recovered = 0

    for job_key, entry in list(index["jobs"].items()):
        state_in_index = entry.get("state", "")
        if state_in_index not in ("PREP_RUNNING", "OCR_RUNNING"):
            continue

        input_name = entry.get("inputName", "unknown")

        # Charger state.json pour récupérer tentatives et inputPath réels
        ok, state_data = safe_load_json(job_state_path(job_key))
        if ok and isinstance(state_data, dict):
            attempt_prep = int(state_data.get("attemptPrep", 1) or 1)
            attempt_ocr = int(state_data.get("attemptOcr", 0) or 0)
            input_path = (
                (state_data.get("input") or {}).get("path")
                or os.path.join(work_dir, job_key, input_name)
            )
        else:
            # Fallback : state absent/corrompu — le run interrompu compte comme 1 tentative
            attempt_prep = 1 if state_in_index == "PREP_RUNNING" else 0
            attempt_ocr = 1 if state_in_index == "OCR_RUNNING" else 0
            input_path = os.path.join(work_dir, job_key, input_name)

        if state_in_index == "PREP_RUNNING":
            if attempt_prep >= max_prep:
                _log.warning(
                    "recover: job %s dépasse max_attempts_prep=%d => ERROR",
                    job_key, max_prep,
                )
                update_state(job_key, {
                    "state": "ERROR",
                    "step": "PREP",
                    "message": "max_attempts_after_restart",
                })
                index["jobs"][job_key]["state"] = "ERROR_PREP"
                save_index(index, index_path)
                continue
            stage = "PREP_RETRY"
        else:  # OCR_RUNNING
            if attempt_ocr >= max_ocr:
                _log.warning(
                    "recover: job %s dépasse max_attempts_ocr=%d => ERROR",
                    job_key, max_ocr,
                )
                update_state(job_key, {
                    "state": "ERROR",
                    "step": "OCR",
                    "message": "max_attempts_after_restart",
                })
                index["jobs"][job_key]["state"] = "ERROR_OCR"
                save_index(index, index_path)
                continue
            stage = "OCR_RETRY"

        meta = {
            "stage": stage,
            "inputName": input_name,
            "inputPath": input_path,
            "attemptPrep": attempt_prep,
            "attemptOcr": attempt_ocr,
        }
        # Conserver rawPdf si le job était en OCR_RUNNING
        if state_in_index == "OCR_RUNNING" and ok and isinstance(state_data, dict):
            raw_pdf = state_data.get("rawPdf") or os.path.join(work_dir, job_key, "raw.pdf")
            meta["rawPdf"] = raw_pdf

        in_flight[job_key] = meta
        _log.info(
            "Recovered job %s stage=%s attemptPrep=%d attemptOcr=%d",
            job_key, stage, attempt_prep, attempt_ocr,
        )
        recovered += 1

    if recovered:
        _log.info("Bootstrap : %d job(s) récupéré(s) après redémarrage", recovered)


# ---------------------------------------------------------------------------
# Doublons
# ---------------------------------------------------------------------------

def write_duplicate_report(job_key: str, incoming_path: str, existing: dict, profile: dict):
    """
    Déplace le fichier entrant dans hold/duplicates et crée le rapport JSON.

    :param job_key: Clé du job doublon.
    :param incoming_path: Chemin du fichier entrant (sera déplacé).
    :param existing: Entrée existante dans l'index.
    :param profile: Profil canonique utilisé.
    """
    ensure_dir(os.path.join(HOLD_DUP_DIR, job_key))
    ensure_dir(DUP_REPORTS_DIR)

    ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    hold_name = f"{ts}__{os.path.basename(incoming_path)}"
    hold_path = os.path.join(HOLD_DUP_DIR, job_key, hold_name)
    move_atomic(incoming_path, hold_path)

    report = {
        "jobKey": job_key,
        "detectedAt": now_iso(),
        "incoming": {
            "fileName": os.path.basename(hold_path),
            "path": hold_path,
            "sizeBytes": os.path.getsize(hold_path),
        },
        "existing": existing,
        "profile": profile,
        "actions": ["USE_EXISTING_RESULT", "DISCARD", "FORCE_REPROCESS"],
    }
    atomic_write_json(os.path.join(DUP_REPORTS_DIR, f"{job_key}.json"), report)
    atomic_write_json(
        os.path.join(HOLD_DUP_DIR, job_key, "status.json"),
        {"jobKey": job_key, "state": "DUPLICATE_PENDING", "updatedAt": now_iso()},
    )


def check_duplicate_decisions(index: dict, index_path: str):
    """
    Applique les décisions utilisateur (decision.json) pour les doublons en attente.
    Modifie ``index`` en place si nécessaire et persiste.

    :param index: Dict de l'index des jobs (modifié en place).
    :param index_path: Chemin du fichier d'index pour la persistance.
    """
    for job_key in list(os.listdir(HOLD_DUP_DIR)):
        job_hold = os.path.join(HOLD_DUP_DIR, job_key)
        if not os.path.isdir(job_hold):
            continue
        decision_path = os.path.join(job_hold, "decision.json")
        if not os.path.exists(decision_path):
            continue
        decision = read_json(decision_path) or {}
        action = decision.get("action")
        existing = index["jobs"].get(job_key)
        held_files = sorted(
            f for f in os.listdir(job_hold) if f.lower().endswith((".cbz", ".cbr"))
        )
        held_file_path = os.path.join(job_hold, held_files[0]) if held_files else None

        if action == "USE_EXISTING_RESULT" and existing and existing.get("outPdf"):
            try:
                out_pdf = output_path_for(
                    os.path.basename(held_file_path) if held_file_path else "duplicate.cbz",
                    job_key,
                )
                ensure_dir(OUT_DIR)
                if not os.path.exists(out_pdf):
                    shutil.copy2(existing["outPdf"], out_pdf)
            except Exception:
                pass
            if held_file_path:
                ensure_dir(ARCHIVE_DIR)
                move_atomic(held_file_path, os.path.join(ARCHIVE_DIR, os.path.basename(held_file_path)))
        elif action == "DISCARD":
            if held_file_path:
                os.remove(held_file_path)
        elif action == "FORCE_REPROCESS":
            nonce = decision.get("nonce") or sha256_str(now_iso())
            if held_file_path:
                new_name = (
                    base_name(held_file_path)
                    + f"__force-{nonce[:8]}"
                    + os.path.splitext(held_file_path)[1]
                )
                move_atomic(held_file_path, os.path.join(IN_DIR, new_name))

        # Nettoyage
        for p in [decision_path,
                  os.path.join(DUP_REPORTS_DIR, f"{job_key}.json"),
                  os.path.join(job_hold, "status.json")]:
            try:
                os.remove(p)
            except FileNotFoundError:
                pass
        try:
            if not os.listdir(job_hold):
                os.rmdir(job_hold)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Soumission + polling HTTP
# ---------------------------------------------------------------------------

def submit_prep(job_key: str, input_path: str):
    """
    Soumet un job de préparation au prep-service.

    :param job_key: Identifiant du job.
    :param input_path: Chemin du fichier d'entrée.
    :raises RuntimeError: Si le service répond avec un code d'erreur.
    """
    r = requests.post(
        PREP_URL + "/jobs/prep",
        json={"jobId": job_key, "inputPath": input_path, "workDir": WORK_DIR},
        timeout=10,
    )
    if r.status_code not in (200, 202):
        raise RuntimeError(f"prep submit failed: {r.status_code} {r.text}")


def submit_ocr(job_key: str, raw_pdf: str):
    """
    Soumet un job OCR à l'ocr-service.

    :param job_key: Identifiant du job.
    :param raw_pdf: Chemin du raw.pdf produit par le prep-service.
    :raises RuntimeError: Si le service répond avec un code d'erreur.
    """
    r = requests.post(
        OCR_URL + "/jobs/ocr",
        json={
            "jobId": job_key,
            "rawPdfPath": raw_pdf,
            "workDir": WORK_DIR,
            "lang": OCR_LANG,
            "rotatePages": True,
            "deskew": True,
            "optimize": 1,
        },
        timeout=10,
    )
    if r.status_code not in (200, 202):
        raise RuntimeError(f"ocr submit failed: {r.status_code} {r.text}")


def poll_job(url: str, job_key: str) -> dict:
    """
    Interroge l'état d'un job sur un service.

    :param url: URL de base du service.
    :param job_key: Identifiant du job.
    :return: Dict JSON de l'état du job.
    :raises RuntimeError: Si le service répond avec un code d'erreur.
    """
    r = requests.get(url + f"/jobs/{job_key}", timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"job status failed: {r.status_code} {r.text}")
    return r.json()


# ---------------------------------------------------------------------------
# Heartbeat-check
# ---------------------------------------------------------------------------

def check_stale_jobs(in_flight: dict, timeout_s: int):
    """
    Vérifie les heartbeats des jobs en cours d'exécution.
    Bascule en ``*_RETRY`` les jobs dont le heartbeat est trop ancien.
    Respecte les limites ``MAX_ATTEMPTS_PREP``/``MAX_ATTEMPTS_OCR`` :
    si le maximum est atteint, bascule directement en ``ERROR``.

    :param in_flight: Dict des jobs en vol (modifié en place).
    :param timeout_s: Délai en secondes avant de considérer un heartbeat stale.
    """
    for job_key, meta in list(in_flight.items()):
        stage = meta.get("stage", "")
        if stage == "PREP_RUNNING":
            hb_path = os.path.join(WORK_DIR, job_key, "prep.heartbeat")
            if is_heartbeat_stale(hb_path, timeout_s):
                update_state(job_key, {
                    "state": "PREP_TIMEOUT",
                    "message": f"heartbeat stale after {timeout_s}s",
                })
                meta["stage"] = "PREP_RETRY"
        elif stage == "OCR_RUNNING":
            hb_path = os.path.join(WORK_DIR, job_key, "ocr.heartbeat")
            if is_heartbeat_stale(hb_path, timeout_s):
                update_state(job_key, {
                    "state": "OCR_TIMEOUT",
                    "message": f"heartbeat stale after {timeout_s}s",
                })
                meta["stage"] = "OCR_RETRY"


# ---------------------------------------------------------------------------
# Tick (logique principale d'un cycle, sans sleep — testable unitairement)
# ---------------------------------------------------------------------------

def process_tick(in_flight: dict, index: dict, index_path: str, profile: dict, config: dict):
    """
    Exécute un cycle complet de l'orchestrateur :
    1. Décisions doublons
    2. Découverte de nouveaux fichiers (si capacité)
    3. Planification des soumissions PREP
    4. Polling des jobs PREP
    5. Planification des soumissions OCR
    6. Polling des jobs OCR + finalisation
    7. Vérification des heartbeats périmés
    8. Mise à jour des métriques

    :param in_flight: Dict des jobs en vol (modifié en place).
    :param index: Dict de l'index des jobs (modifié en place).
    :param index_path: Chemin du fichier d'index pour la persistance.
    :param profile: Profil canonique courant.
    :param config: Dict de configuration avec les clés :
                   ``prep_url``, ``ocr_url``, ``work_dir``, ``max_jobs_in_flight``,
                   ``prep_concurrency``, ``ocr_concurrency``,
                   ``max_attempts_prep``, ``max_attempts_ocr``,
                   ``job_timeout_s``, ``index_dir``, ``metrics``.
    """
    metrics: dict = config.get("metrics", make_empty_metrics())

    check_duplicate_decisions(index, index_path)

    # -- Découverte --
    if len(in_flight) < config["max_jobs_in_flight"]:
        for src in list(discover_inputs()):
            ts = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
            original_name = os.path.basename(src)
            staging_path = os.path.join(config["work_dir"], "_staging", ts + "_" + original_name)
            ensure_dir(os.path.dirname(staging_path))
            try:
                move_atomic(src, staging_path)
            except Exception:
                continue

            # E1 — Vérification taille fichier
            if not check_input_size(staging_path, config.get("max_input_size_mb", MAX_INPUT_SIZE_MB)):
                _log.warning("Fichier trop grand, rejeté", extra={"stage": "INPUT_CHECK"})
                err_dst = os.path.join(ERROR_DIR, os.path.basename(staging_path))
                try:
                    move_atomic(staging_path, err_dst)
                except Exception:
                    pass
                update_metrics(metrics, "input_rejected_size")
                continue

            # E2 — Vérification signature ZIP/RAR
            if not check_file_signature(staging_path):
                _log.warning("Signature invalide, rejeté", extra={"stage": "INPUT_CHECK"})
                err_dst = os.path.join(ERROR_DIR, os.path.basename(staging_path))
                try:
                    move_atomic(staging_path, err_dst)
                except Exception:
                    pass
                update_metrics(metrics, "input_rejected_signature")
                continue

            file_hash = sha256_file(staging_path)
            _, job_key = make_job_key(file_hash, profile)

            # B4 — Vérification espace disque avant PREP
            input_size = os.path.getsize(staging_path)
            if not check_disk_space(config["work_dir"], input_size, config.get("disk_free_factor", DISK_FREE_FACTOR)):
                _log.error("Espace disque insuffisant", extra={"stage": "DISK_CHECK"})
                err_dst = os.path.join(ERROR_DIR, os.path.basename(staging_path))
                try:
                    move_atomic(staging_path, err_dst)
                except Exception:
                    pass
                update_metrics(metrics, "disk_error")
                continue

            existing = index["jobs"].get(job_key)
            if existing:
                write_duplicate_report(job_key, staging_path, existing, profile)
                continue

            jdir = job_dir(job_key)
            ensure_dir(jdir)
            input_path = os.path.join(jdir, original_name)
            move_atomic(staging_path, input_path)

            profile_hash, _ = make_job_key(file_hash, profile)
            update_state(job_key, {
                "state": "DISCOVERED",
                "profile": profile,
                "fileHash": file_hash,
                "profileHash": profile_hash,
                "input": {"name": original_name, "path": input_path},
            })
            index["jobs"][job_key] = {
                "jobKey": job_key,
                "state": "DISCOVERED",
                "inputName": original_name,
                "outPdf": None,
                "updatedAt": now_iso(),
            }
            save_index(index, index_path)
            in_flight[job_key] = {
                "stage": "DISCOVERED",
                "inputName": original_name,
                "inputPath": input_path,
                "attemptPrep": 0,
                "attemptOcr": 0,
            }
            update_metrics(metrics, "queued")
            break  # un fichier par tick

    # -- Planification PREP --
    running_prep = sum(1 for j in in_flight.values() if j["stage"] == "PREP_RUNNING")
    can_start_prep = max(0, config["prep_concurrency"] - running_prep)
    for job_key, meta in list(in_flight.items()):
        if can_start_prep <= 0:
            break
        if meta["stage"] in ("DISCOVERED", "PREP_RETRY"):
            if meta["attemptPrep"] >= config["max_attempts_prep"]:
                update_state(job_key, {"state": "ERROR", "step": "PREP", "message": "max attempts reached"})
                index["jobs"][job_key]["state"] = "ERROR_PREP"
                save_index(index, index_path)
                try:
                    move_atomic(meta["inputPath"], os.path.join(ERROR_DIR, os.path.basename(meta["inputPath"])))
                except Exception:
                    pass
                del in_flight[job_key]
                update_metrics(metrics, "error")
                continue
            meta["attemptPrep"] += 1
            update_state(job_key, {"state": "PREP_SUBMITTED", "step": "PREP", "attempt": meta["attemptPrep"]})
            try:
                submit_prep(job_key, meta["inputPath"])
                meta["stage"] = "PREP_RUNNING"
                index["jobs"][job_key]["state"] = "PREP_RUNNING"
                save_index(index, index_path)
                update_metrics(metrics, "running")
                can_start_prep -= 1
            except Exception as e:
                update_state(job_key, {"state": "ERROR", "step": "PREP", "message": str(e)})
                meta["stage"] = "PREP_RETRY"

    # -- Polling PREP --
    for job_key, meta in list(in_flight.items()):
        if meta["stage"] != "PREP_RUNNING":
            continue
        try:
            st = poll_job(config["prep_url"], job_key)
            if st.get("state") == "DONE":
                raw_pdf = st.get("artifacts", {}).get("rawPdf") or os.path.join(job_dir(job_key), "raw.pdf")
                update_state(job_key, {"state": "PREP_DONE", "step": "PREP", "rawPdf": raw_pdf})
                meta["rawPdf"] = raw_pdf
                meta["stage"] = "PREP_DONE"
                index["jobs"][job_key]["state"] = "PREP_DONE"
                save_index(index, index_path)
            elif st.get("state") == "ERROR":
                update_state(job_key, {"state": "PREP_ERROR", "step": "PREP", "message": st.get("message")})
                meta["stage"] = "PREP_RETRY"
        except Exception:
            pass

    # -- Planification OCR --
    running_ocr = sum(1 for j in in_flight.values() if j["stage"] == "OCR_RUNNING")
    can_start_ocr = max(0, config["ocr_concurrency"] - running_ocr)
    for job_key, meta in list(in_flight.items()):
        if can_start_ocr <= 0:
            break
        if meta["stage"] in ("PREP_DONE", "OCR_RETRY"):
            if meta["attemptOcr"] >= config["max_attempts_ocr"]:
                update_state(job_key, {"state": "ERROR", "step": "OCR", "message": "max attempts reached"})
                index["jobs"][job_key]["state"] = "ERROR_OCR"
                save_index(index, index_path)
                del in_flight[job_key]
                update_metrics(metrics, "error")
                continue
            meta["attemptOcr"] += 1
            raw_pdf = meta.get("rawPdf") or os.path.join(job_dir(job_key), "raw.pdf")
            update_state(job_key, {"state": "OCR_SUBMITTED", "step": "OCR", "attempt": meta["attemptOcr"], "rawPdf": raw_pdf})
            try:
                submit_ocr(job_key, raw_pdf)
                meta["stage"] = "OCR_RUNNING"
                index["jobs"][job_key]["state"] = "OCR_RUNNING"
                save_index(index, index_path)
                can_start_ocr -= 1
            except Exception as e:
                update_state(job_key, {"state": "ERROR", "step": "OCR", "message": str(e)})
                meta["stage"] = "OCR_RETRY"

    # -- Polling OCR + finalisation --
    for job_key, meta in list(in_flight.items()):
        if meta["stage"] != "OCR_RUNNING":
            continue
        try:
            st = poll_job(config["ocr_url"], job_key)
            if st.get("state") == "DONE":
                final_pdf = st.get("artifacts", {}).get("finalPdf") or os.path.join(job_dir(job_key), "final.pdf")

                # B3 — Validation PDF avant move vers /out
                min_pdf = config.get("min_pdf_size_bytes", MIN_PDF_SIZE_BYTES)
                if not validate_pdf(final_pdf, min_size_bytes=min_pdf):
                    _log.error("PDF final invalide", extra={"jobKey": job_key, "stage": "OCR_FINALIZE"})
                    update_state(job_key, {"state": "OCR_ERROR", "step": "OCR", "message": "pdf_invalid"})
                    meta["stage"] = "OCR_RETRY"
                    update_metrics(metrics, "pdf_invalid")
                    continue

                out_pdf = output_path_for(meta["inputName"], job_key)
                ensure_dir(OUT_DIR)
                move_atomic(final_pdf, out_pdf)
                _log.info("Job terminé", extra={"jobKey": job_key, "stage": "DONE"})
                update_state(job_key, {"state": "DONE", "step": "OCR", "finalPdf": out_pdf})
                index["jobs"][job_key]["state"] = "DONE"
                index["jobs"][job_key]["outPdf"] = out_pdf
                save_index(index, index_path)

                # B5 — Nettoyage workdir immédiat si KEEP_WORK_DIR_DAYS=0
                keep_days = config.get("keep_work_dir_days", KEEP_WORK_DIR_DAYS)
                if keep_days == 0:
                    try:
                        shutil.rmtree(job_dir(job_key), ignore_errors=True)
                    except Exception:
                        pass

                try:
                    ensure_dir(ARCHIVE_DIR)
                    move_atomic(meta["inputPath"], os.path.join(ARCHIVE_DIR, os.path.basename(meta["inputPath"])))
                except Exception:
                    pass
                del in_flight[job_key]
                update_metrics(metrics, "done")
            elif st.get("state") == "ERROR":
                update_state(job_key, {"state": "OCR_ERROR", "step": "OCR", "message": st.get("message")})
                meta["stage"] = "OCR_RETRY"
        except Exception:
            pass

    # -- Heartbeat-check --
    check_stale_jobs(in_flight, config.get("job_timeout_s", JOB_TIMEOUT_SECONDS))

    # -- Métriques --
    write_metrics(metrics, config.get("index_dir", INDEX_DIR))


# ---------------------------------------------------------------------------
# Boucle principale
# ---------------------------------------------------------------------------

def process_loop():
    """
    Boucle principale de l'orchestrateur.
    Initialise le layout, récupère les infos de services,
    puis appelle ``process_tick`` en boucle infinie.
    Démarre également le serveur HTTP d'observabilité et le janitor workdir.
    """
    ensure_layout()
    _log.info("Orchestrateur démarré")
    prep_info = get_service_info(PREP_URL)
    ocr_info = get_service_info(OCR_URL)
    profile = canonical_profile(prep_info, ocr_info, OCR_LANG)

    index, index_path = load_index()
    in_flight: dict = {}
    metrics = make_empty_metrics()

    config = {
        "prep_url": PREP_URL,
        "ocr_url": OCR_URL,
        "work_dir": WORK_DIR,
        "max_jobs_in_flight": MAX_JOBS_IN_FLIGHT,
        "prep_concurrency": PREP_CONCURRENCY,
        "ocr_concurrency": OCR_CONCURRENCY,
        "max_attempts_prep": MAX_ATTEMPTS_PREP,
        "max_attempts_ocr": MAX_ATTEMPTS_OCR,
        "job_timeout_s": JOB_TIMEOUT_SECONDS,
        "index_dir": INDEX_DIR,
        "metrics": metrics,
        # Robustesse FS
        "keep_work_dir_days": KEEP_WORK_DIR_DAYS,
        "min_pdf_size_bytes": MIN_PDF_SIZE_BYTES,
        "disk_free_factor": DISK_FREE_FACTOR,
        # Hardening
        "max_input_size_mb": MAX_INPUT_SIZE_MB,
    }

    # Bootstrap : reprise des jobs interrompus avant le premier tick
    recover_running_jobs(index, index_path, in_flight, config)

    # Démarrage serveur HTTP observabilité (C)
    orch_state = OrchestratorState(
        in_flight=in_flight,
        metrics=metrics,
        config=config,
        work_dir=WORK_DIR,
        index_path=index_path,
    )
    try:
        start_http_server(orch_state, port=ORCHESTRATOR_HTTP_PORT, bind=ORCHESTRATOR_HTTP_BIND)
        _log.info(f"Serveur HTTP démarré sur {ORCHESTRATOR_HTTP_BIND}:{ORCHESTRATOR_HTTP_PORT}")
    except Exception as e:
        _log.warning(f"Impossible de démarrer le serveur HTTP : {e}")

    # Janitor workdir périodique (B5) — toutes les 600s
    _janitor_last_run = [0.0]

    def _run_janitor():
        keep_days = config.get("keep_work_dir_days", KEEP_WORK_DIR_DAYS)
        if keep_days > 0:
            running_keys = set(in_flight.keys())
            deleted = cleanup_old_workdirs(WORK_DIR, keep_days, running_keys)
            if deleted:
                _log.info(f"Janitor : {deleted} workdir(s) supprimé(s)")

    while True:
        ensure_layout()
        process_tick(in_flight, index, index_path, profile, config)

        # Janitor workdir toutes les 600 secondes
        now = time.time()
        if now - _janitor_last_run[0] > 600:
            _run_janitor()
            _janitor_last_run[0] = now

        time.sleep(POLL_INTERVAL_MS / 1000.0)


if __name__ == "__main__":
    process_loop()
