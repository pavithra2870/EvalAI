"""Structured JSON logger. Usage: log.info({"event": "foo", "key": "val"})"""
import json
import logging
import sys


class _JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        try:
            data = json.loads(msg)
        except (json.JSONDecodeError, TypeError):
            data = {"msg": msg}
        data["level"] = record.levelname
        data["logger"] = record.name
        if record.exc_info:
            data["exc"] = self.formatException(record.exc_info)
        return json.dumps(data)


class StructuredLogger:
    def __init__(self, name: str) -> None:
        self._raw = logging.getLogger(name)
        if not self._raw.handlers:
            h = logging.StreamHandler(sys.stdout)
            h.setFormatter(_JSONFormatter())
            self._raw.addHandler(h)
            self._raw.setLevel(logging.INFO)
        self._raw.propagate = False

    def info(self, data: dict) -> None:
        self._raw.info(json.dumps(data))

    def warning(self, data: dict) -> None:
        self._raw.warning(json.dumps(data))

    def error(self, data: dict) -> None:
        self._raw.error(json.dumps(data))


def get_logger(name: str) -> StructuredLogger:
    return StructuredLogger(name)
