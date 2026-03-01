"""
Helper de logging structuré pour l'ocr-service.
Logs vers stdout ET fichier rotatif (RotatingFileHandler stdlib).

Variables d'environnement :
  LOG_DIR              : répertoire de logs (défaut : /data/logs)
  LOG_FILE             : nom du fichier log (défaut : ocr-service.log)
  LOG_JSON             : true/1/yes => format JSON lines (défaut : false)
  LOG_LEVEL            : niveau de log (défaut : INFO)
  LOG_ROTATE_MAX_BYTES : taille max avant rotation en octets (défaut : 10_000_000)
  LOG_ROTATE_BACKUPS   : nombre de fichiers de sauvegarde (défaut : 5)
"""
import json
import logging
import logging.handlers
import os
import time

_LOG_JSON = os.environ.get("LOG_JSON", "false").lower() in ("true", "1", "yes")
_SERVICE = "ocr-service"
_LOG_DIR = os.environ.get("LOG_DIR", "/data/logs")
_LOG_FILE = os.environ.get("LOG_FILE", "ocr-service.log")
_LOG_LEVEL = getattr(logging, os.environ.get("LOG_LEVEL", "INFO").upper(), logging.INFO)
_LOG_ROTATE_MAX_BYTES = int(os.environ.get("LOG_ROTATE_MAX_BYTES", "10000000"))
_LOG_ROTATE_BACKUPS = int(os.environ.get("LOG_ROTATE_BACKUPS", "5"))


class _JsonFormatter(logging.Formatter):
    """Formatter JSON ligne par ligne."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "level": record.levelname,
            "service": _SERVICE,
            "message": record.getMessage(),
        }
        for key in ("jobKey", "stage", "attempt"):
            val = getattr(record, key, None)
            if val is not None:
                payload[key] = val
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str = _SERVICE) -> logging.Logger:
    """
    Retourne un logger configuré : stdout + fichier rotatif.

    :param name: Nom du logger (défaut : ``ocr-service``).
    :return: Instance ``logging.Logger`` configurée.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        formatter = _JsonFormatter() if _LOG_JSON else logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
        os.makedirs(_LOG_DIR, exist_ok=True)
        log_path = os.path.join(_LOG_DIR, _LOG_FILE)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=_LOG_ROTATE_MAX_BYTES,
            backupCount=_LOG_ROTATE_BACKUPS,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(_LOG_LEVEL)
        logger.propagate = False
    return logger


def reset_logger_for_tests(logger: logging.Logger) -> None:
    """
    Ferme et supprime tous les handlers d'un logger.
    À utiliser uniquement dans les tests pour éviter les fuites d'état entre tests.

    :param logger: Le logger à réinitialiser.
    """
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

