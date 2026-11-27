"""Structured JSON logging to stdout, with credentials removed."""

import json
import logging
import re
import sys
from typing import Any

from app.core.time import utc_now

SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie"}
REMOVED = "[removed]"

# Catches "Cookie: a=1; b=2" or "authorization=Bearer x" inside free-text messages.
# Everything to the end of the line goes, since cookie and token values contain spaces and ";".
SENSITIVE_IN_TEXT = re.compile(r"(?i)\b(authorization|set-cookie|cookie)(\s*[:=]\s*)[^\r\n]*")

# Attributes every LogRecord has; anything else was passed through `extra=`.
STANDARD_ATTRIBUTES = set(vars(logging.makeLogRecord({}))) | {"message", "asctime"}


def redact(value: Any) -> Any:
    """Return a copy of value with sensitive header values replaced, at any depth."""
    if isinstance(value, dict):
        return {
            key: REMOVED if str(key).lower() in SENSITIVE_HEADERS else redact(item)
            for key, item in value.items()
        }
    if isinstance(value, list | tuple):
        return [redact(item) for item in value]
    if isinstance(value, str):
        return SENSITIVE_IN_TEXT.sub(rf"\1\2{REMOVED}", value)
    return value


class JsonFormatter(logging.Formatter):
    """Format each record as one JSON line."""

    def format(self, record: logging.LogRecord) -> str:
        """Build the JSON line from the record and any extra fields."""
        entry: dict[str, Any] = {
            "time": utc_now().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in vars(record).items():
            if key not in STANDARD_ATTRIBUTES:
                entry[key] = value
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(redact(entry), default=str)


def configure_logging(level: str = "INFO") -> None:
    """Send every log, including Uvicorn's, to stdout as JSON."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Uvicorn installs its own handlers; route its logs through ours instead.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = []
        uvicorn_logger.propagate = True
