"""
Helper de logging structuré pour le prep-service.
Si LOG_JSON=true, chaque log est émis sous forme de ligne JSON.
"""

import json
import logging
import os
import time
import sys
import traceback

_LOG_JSON = os.environ.get("LOG_JSON", "false").lower() in ("true", "1", "yes")
_SERVICE = "prep-service"


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
    """Retourne un logger structuré pour le prep-service."""
    logger = logging.getLogger(name)
    # Force re-wrapping so tests that reload with different LOG_JSON get correct behavior
    try:
        delattr(logger, "_structured_wrapped")
    except Exception:
        pass

    if not logger.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(h)
        if logger.level == logging.NOTSET:
            logger.setLevel(logging.INFO)
        logger.propagate = False

    # Save originals
    orig_debug = logger.debug
    orig_info = logger.info
    orig_warning = logger.warning
    orig_error = logger.error
    orig_exception = logger.exception

    def _make_wrapper(level_name):
        def _wrapped(msg, *args, **kwargs):
            extra = kwargs.get("extra")
            exc_info = kwargs.get("exc_info")
            exc = None
            if exc_info:
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
            record_level = getattr(logging, level_name, logging.INFO)
            record = logging.LogRecord(
                name=logger.name,
                level=record_level,
                pathname=__file__,
                lineno=0,
                msg=formatted,
                args=(),
                exc_info=None,
            )
            if extra:
                for k, v in extra.items():
                    setattr(record, k, v)
            for h in list(logger.handlers):
                try:
                    h.emit(record)
                except Exception:
                    try:
                        logging.getLogger("stderr").error(
                            "Log handler error", exc_info=True
                        )
                    except Exception:
                        pass
            return None

        return _wrapped

    logger.debug = _make_wrapper("DEBUG")
    logger.info = _make_wrapper("INFO")
    logger.warning = _make_wrapper("WARNING")
    logger.error = _make_wrapper("ERROR")

    def _exception_wrapper(msg, *args, **kwargs):
        kwargs = dict(kwargs)
        kwargs["exc_info"] = kwargs.get("exc_info", True)
        return logger.error(msg, *args, **kwargs)

    logger.exception = _exception_wrapper
    logger._structured_wrapped = True
    return logger
