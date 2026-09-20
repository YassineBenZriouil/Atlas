"""Structured logging setup. Logs MUST NEVER contain secrets (Atlas.md section 36)."""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_SENSITIVE_PATTERNS = [
    re.compile(r"(password\s*=\s*)\S+", re.IGNORECASE),
    re.compile(r"(client_secret\s*=\s*)\S+", re.IGNORECASE),
    re.compile(r"(access_token\s*=\s*)\S+", re.IGNORECASE),
    re.compile(r"(refresh_token\s*=\s*)\S+", re.IGNORECASE),
    re.compile(r"(api_key\s*=\s*)\S+", re.IGNORECASE),
]


class RedactingFilter(logging.Filter):
    """Strips common secret patterns out of log messages before they are written."""

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        redacted = message
        for pattern in _SENSITIVE_PATTERNS:
            redacted = pattern.sub(r"\1***REDACTED***", redacted)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def configure_logging(
    log_dir: Path,
    *,
    level: str = "INFO",
    max_bytes: int = 5_000_000,
    backup_count: int = 5,
) -> None:
    root = logging.getLogger("atlas")
    root.setLevel(level.upper())
    root.handlers.clear()

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)
    redactor = RedactingFilter()

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    console.addFilter(redactor)
    root.addHandler(console)

    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        log_dir / "atlas.log",
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(redactor)
    root.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"atlas.{name}")
