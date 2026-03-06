"""
Helper de logging structuré pour l'ocr-service.
Si LOG_JSON=true, chaque log est émis sous forme de ligne JSON.
"""

import json
import logging
import os
import time
import sys
import traceback

_LOG_JSON = os.environ.get("LOG_JSON", "false").lower() in ("true", "1", "yes")
_SERVICE = "ocr-service"


def _iso_now(ts: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def _format_payload(
    level_name: str, message: str, extra: dict | None = None, exc: tuple | None = None
) -> str:
    payload = {
        "timestamp": _iso_now(time.time()),
        "level": level_name,
        "service": _SERVICE,
        "message": message,
    }
    if extra:
        for key in ("jobKey", "stage", "attempt"):
            if key in extra:
                payload[key] = extra[key]
    if exc:
        payload["exception"] = "".join(traceback.format_exception(*exc))
    return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str = _SERVICE) -> logging.Logger:
    """
    Retourne un logger configuré selon LOG_JSON.

    Le logger retourné est une instance de ``logging.Logger`` (API inchangée),
    mais ses méthodes `debug/info/warning/error/exception` sont remplacées
    par des wrappers qui pré-formattent le message (JSON ou texte) avant
    de le passer aux handlers. Cela permet aux tests qui attachent un
    handler de capture sans formatter d'obtenir la sortie attendue.
    """
    logger = logging.getLogger(name)
    # Force re-wrapping on each call so tests that reload the module with
    # a different LOG_JSON value get the correct behavior. We explicitly
    # clear the previous marker so wrappers are recreated below.
    try:
        delattr(logger, "_structured_wrapped")
    except Exception:
        pass
    # config initiale du handler par défaut si le logger n'a pas de handlers
    if not logger.handlers:
        handler = logging.StreamHandler()
        # on laisse la possibilité d'ajouter des formatters externes — tests
        # ajoutent leur handler capture sans formatter, donc on pré-formatte
        # les messages plus bas pour garantir le comportement attendu.
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)
        # Respecter le niveau si le test a préalablement défini DEBUG
        if logger.level == logging.NOTSET:
            logger.setLevel(logging.INFO)
        logger.propagate = False

    # Always (re)wrap: we deleted _structured_wrapped above to force recreation

    # Sauvegarder les méthodes originales
    orig_debug = logger.debug
    orig_info = logger.info
    orig_warning = logger.warning
    orig_error = logger.error
    orig_exception = logger.exception

    def _make_wrapper(orig_method, level_name):
        def _wrapped(msg, *args, **kwargs):
            extra = kwargs.get("extra")
            # Détecter exception courante si fournie explicitement ou via exc_info
            exc_info = kwargs.get("exc_info")
            exc = None
            if exc_info:
                # si exc_info est True, prendre l'exception courante
                if exc_info is True:
                    exc = sys.exc_info()
                else:
                    exc = exc_info
            # Read LOG_JSON at call time to reflect monkeypatch.setenv + reload behavior
            log_json_now = os.environ.get("LOG_JSON", "false").lower() in (
                "true",
                "1",
                "yes",
            )
            if log_json_now:
                formatted = _format_payload(level_name, msg, extra, exc)
            else:
                formatted = f"[{level_name}] {_SERVICE}: {msg}"
            # Émettre explicitement vers les handlers avec un LogRecord pour
            # éviter que les handlers n'ajoutent une trace d'exception séparée.
            record_level = getattr(logging, level_name, logging.INFO)
            # Créer un LogRecord minimal; message déjà formaté
            record = logging.LogRecord(
                name=logger.name,
                level=record_level,
                pathname=__file__,
                lineno=0,
                msg=formatted,
                args=(),
                exc_info=None,
            )
            # Copier extra champs éventuels (non-standard) dans record
            if extra:
                for k, v in extra.items():
                    setattr(record, k, v)
            # Émettre vers chaque handler explicitement
            for h in list(logger.handlers):
                try:
                    h.emit(record)
                except Exception:
                    # Ne jamais laisser un handler planter l'application
                    try:
                        logging.getLogger("stderr").error(
                            "Log handler error", exc_info=True
                        )
                    except Exception:
                        pass
            return None

        return _wrapped

    logger.debug = _make_wrapper(orig_debug, "DEBUG")
    logger.info = _make_wrapper(orig_info, "INFO")
    logger.warning = _make_wrapper(orig_warning, "WARNING")
    logger.error = _make_wrapper(orig_error, "ERROR")

    def _exception_wrapper(msg, *args, **kwargs):
        # s'assurer que exc_info=True est pris en compte par notre wrapper
        kwargs = dict(kwargs)
        kwargs["exc_info"] = kwargs.get("exc_info", True)
        return logger.error(msg, *args, **kwargs)

    logger.exception = _exception_wrapper

    logger._structured_wrapped = True
    return logger
