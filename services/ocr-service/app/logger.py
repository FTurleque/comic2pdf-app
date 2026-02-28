"""
Helper de logging structuré pour l'ocr-service.
Si LOG_JSON=true, chaque log est émis sous forme de ligne JSON.
"""
import json
import logging
import os
import time

_LOG_JSON = os.environ.get("LOG_JSON", "false").lower() in ("true", "1", "yes")
_SERVICE = "ocr-service"


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
    Retourne un logger configuré selon LOG_JSON.

    :param name: Nom du logger.
    :return: Instance ``logging.Logger`` configurée.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        if _LOG_JSON:
            handler.setFormatter(_JsonFormatter())
        else:
            handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%SZ",
            ))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger

