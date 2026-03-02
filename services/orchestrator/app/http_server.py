"""
Serveur HTTP minimal (stdlib http.server) pour l'observabilité de l'orchestrateur.
Endpoints :
  GET  /metrics            -> JSON métriques
  GET  /jobs               -> JSON liste des jobs (depuis index)
  GET  /jobs/{jobKey}      -> JSON state.json du job (404 si absent)
  POST /config             -> met à jour la config runtime (thread-safe) — PROTÉGÉ par X-Api-Key
  GET  /config             -> JSON config courante

Auth :
  POST /config est protégé par le header X-Api-Key.
  Règle (lue à chaque requête depuis l'env var ORCHESTRATOR_API_KEY) :
    - Clé configurée → header requis + comparaison constant-time (hmac.compare_digest).
      Mauvaise clé → 401. Header absent → 401.
    - Clé non configurée → accepter uniquement depuis localhost (127.0.0.1 / ::1).
      Autre IP → 403.
  Les GET restent ouverts (read-only / monitoring).
  Audit log : IP + résultat (sans jamais logger la valeur de la clé).

Démarrage en thread daemon via start_http_server().
"""
import copy
import hmac
import json
import os
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional
from urllib.parse import urlparse

from app.utils import read_json, safe_path
from app.logger import get_logger

_log = get_logger("orchestrator.http")

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

_ENV_API_KEY = "ORCHESTRATOR_API_KEY"
_LOCALHOST_IPS = {"127.0.0.1", "::1", "0:0:0:0:0:0:0:1"}


# ---------------------------------------------------------------------------
# OrchestratorState — état partagé thread-safe
# ---------------------------------------------------------------------------

class OrchestratorState:
    """
    Conteneur thread-safe pour les données partagées entre la boucle principale
    et le handler HTTP.

    La boucle principale garde les références sur in_flight, metrics, config.
    Le handler HTTP lit uniquement des snapshots (deepcopy sous lock).
    Seul POST /config écrit, via update_config(), sous lock.
    """

    def __init__(
        self,
        in_flight: dict,
        metrics: dict,
        config: dict,
        work_dir: str,
        index_path: str,
    ):
        self._lock = threading.Lock()
        self._in_flight = in_flight    # référence directe (pas de copie)
        self._metrics = metrics        # référence directe
        self._config = config          # référence directe
        self._work_dir = work_dir
        self._index_path = index_path

    def snapshot_metrics(self) -> dict:
        """Retourne un snapshot thread-safe des métriques courantes."""
        with self._lock:
            return copy.deepcopy(self._metrics)

    def snapshot_jobs_list(self) -> list:
        """
        Retourne un snapshot de la liste des jobs depuis l'index JSON.
        Lit le fichier d'index sous lock pour éviter une lecture partielle.
        """
        with self._lock:
            idx = read_json(self._index_path) or {"jobs": {}}
            jobs = []
            for job_key, entry in idx.get("jobs", {}).items():
                # Compléter avec les infos in_flight si disponibles
                inflight = self._in_flight.get(job_key, {})
                jobs.append({
                    "jobKey": job_key,
                    "state": entry.get("state", "UNKNOWN"),
                    "stage": inflight.get("stage", entry.get("state", "")),
                    "attempt": max(
                        inflight.get("attemptPrep", 0),
                        inflight.get("attemptOcr", 0),
                    ),
                    "updatedAt": entry.get("updatedAt", ""),
                    "inputName": entry.get("inputName", ""),
                    "outPdf": entry.get("outPdf"),
                    "errorMessage": entry.get("message", ""),
                })
        return jobs

    def snapshot_job(self, job_key: str) -> Optional[dict]:
        """
        Retourne un snapshot du state.json d'un job spécifique.

        :param job_key: Identifiant du job.
        :return: Dict du state.json ou None si absent.
        """
        try:
            state_path = safe_path(self._work_dir, os.path.join(self._work_dir, job_key, "state.json"))
        except ValueError:
            return None
        with self._lock:
            return read_json(state_path)

    def snapshot_config(self) -> dict:
        """Retourne un snapshot thread-safe de la config courante."""
        with self._lock:
            return copy.deepcopy(self._config)

    def update_config(self, patch: dict) -> dict:
        """
        Applique un patch partiel à la config runtime.
        Clés autorisées : prep_concurrency, ocr_concurrency,
        job_timeout_s, default_ocr_lang.

        :param patch: Dict partiel avec les champs à modifier.
        :return: Dict des champs effectivement modifiés.
        """
        _ALLOWED = {
            "prep_concurrency": int,
            "ocr_concurrency": int,
            "job_timeout_s": int,
            "default_ocr_lang": str,
        }
        applied = {}
        with self._lock:
            for key, cast in _ALLOWED.items():
                if key in patch:
                    try:
                        self._config[key] = cast(patch[key])
                        applied[key] = self._config[key]
                    except (ValueError, TypeError):
                        pass
        return applied


# ---------------------------------------------------------------------------
# Handler HTTP
# ---------------------------------------------------------------------------

class _OrchestratorHandler(BaseHTTPRequestHandler):
    """Handler HTTP minimaliste pour l'API d'observabilité."""

    state: OrchestratorState  # injecté via server.state

    def log_message(self, format, *args):
        pass  # Silencer les logs HTTP par défaut

    def _send_json(self, code: int, data) -> None:
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, code: int, message: str) -> None:
        self._send_json(code, {"error": message, "status": code})

    def _get_client_ip(self) -> str:
        """Retourne l'IP du client (supporte les proxies via X-Forwarded-For)."""
        xff = self.headers.get("X-Forwarded-For", "")
        if xff:
            return xff.split(",")[0].strip()
        return self.client_address[0] if self.client_address else "unknown"

    def _check_api_key(self) -> bool:
        """
        Vérifie l'authentification pour les endpoints sensibles (POST /config).

        Règle :
          - ORCHESTRATOR_API_KEY définie → comparer X-Api-Key via hmac.compare_digest.
            Retourne True si ok, False sinon (401 envoyé).
          - ORCHESTRATOR_API_KEY non définie → accepter localhost uniquement.
            Retourne True si localhost, False sinon (403 envoyé).

        Audit log : IP + résultat. La valeur de la clé n'est JAMAIS loguée.

        :return: True si la requête est autorisée, False si refusée (réponse déjà envoyée).
        """
        client_ip = self._get_client_ip()
        expected_key = os.environ.get(_ENV_API_KEY, "")

        if expected_key:
            # Clé configurée : vérification du header
            provided_key = self.headers.get("X-Api-Key", "")
            ok = bool(provided_key) and hmac.compare_digest(
                provided_key.encode("utf-8"),
                expected_key.encode("utf-8"),
            )
            if ok:
                _log.info(f"[AUDIT] POST /config ACCEPTED ip={client_ip}")
            else:
                _log.warning(f"[AUDIT] POST /config REFUSED ip={client_ip} reason=invalid_key")
                self._send_error_json(401, "Authentification requise : header X-Api-Key manquant ou incorrect")
            return ok
        else:
            # Pas de clé configurée : accepter uniquement localhost
            is_local = client_ip in _LOCALHOST_IPS
            if is_local:
                _log.info(f"[AUDIT] POST /config ACCEPTED ip={client_ip} (no-key localhost)")
            else:
                _log.warning(f"[AUDIT] POST /config REFUSED ip={client_ip} reason=no_key_non_local")
                self._send_error_json(403, "POST /config non autorisé depuis une IP non-locale (configurez ORCHESTRATOR_API_KEY)")
            return is_local

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/metrics":
            self._send_json(200, self.server.state.snapshot_metrics())

        elif path == "/jobs":
            self._send_json(200, self.server.state.snapshot_jobs_list())

        elif path.startswith("/jobs/"):
            job_key = path[len("/jobs/"):]
            if not job_key:
                self._send_error_json(400, "jobKey manquant dans l'URL")
                return
            data = self.server.state.snapshot_job(job_key)
            if data is None:
                self._send_error_json(404, f"Job inconnu : {job_key}")
            else:
                self._send_json(200, data)

        elif path == "/config":
            self._send_json(200, self.server.state.snapshot_config())

        else:
            self._send_error_json(404, f"Route inconnue : {path}")

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/config":
            # Auth obligatoire sur POST /config
            if not self._check_api_key():
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(length)
                patch = json.loads(body)
                if not isinstance(patch, dict):
                    self._send_error_json(400, "Le payload doit être un objet JSON")
                    return
                applied = self.server.state.update_config(patch)
                self._send_json(200, {"applied": applied})
            except (json.JSONDecodeError, ValueError) as e:
                self._send_error_json(400, f"JSON invalide : {e}")
        else:
            self._send_error_json(404, f"Route inconnue : {path}")


class _OrchestratorHTTPServer(HTTPServer):
    """Serveur HTTP avec référence vers l'état partagé."""

    def __init__(self, server_address, state: OrchestratorState):
        super().__init__(server_address, _OrchestratorHandler)
        self.state = state


# ---------------------------------------------------------------------------
# Démarrage public
# ---------------------------------------------------------------------------

def start_http_server(state: OrchestratorState, port: int = 8080, bind: str = "0.0.0.0") -> HTTPServer:
    """
    Démarre le serveur HTTP d'observabilité dans un thread daemon.

    :param state: Instance OrchestratorState partagée avec la boucle principale.
    :param port: Port TCP d'écoute (défaut : 8080).
    :param bind: Adresse IP de bind (défaut : 0.0.0.0).
    :return: Instance du serveur HTTP démarré.
    """
    server = _OrchestratorHTTPServer((bind, port), state)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    return server

