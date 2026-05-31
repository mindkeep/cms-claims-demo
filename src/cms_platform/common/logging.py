import json
import logging
import sys
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data: dict[str, object] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if getattr(record, "audit", False):
            data["audit"] = True
            data["beneficiary_id"] = getattr(record, "beneficiary_id", None)
            data["action"] = getattr(record, "action", None)
            data["accessor"] = getattr(record, "accessor", None)
            data["context"] = getattr(record, "context", {})
        return json.dumps(data)


def configure_logging(level: str = "INFO") -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logging.basicConfig(level=level, handlers=[handler], force=True)
