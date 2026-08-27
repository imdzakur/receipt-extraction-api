import json
import logging
import sys
from pathlib import Path

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

_logger = logging.getLogger("receipt.requests")
_logger.setLevel(logging.INFO)
_logger.propagate = False

if not _logger.handlers:
    _logger.addHandler(logging.StreamHandler(sys.stdout))
    _logger.addHandler(
        logging.FileHandler(LOG_DIR / "requests.jsonl", encoding="utf-8")
    )


def log_request(**fields) -> None:
    """Tulis satu baris JSON ke stdout dan ke logs/requests.jsonl."""
    _logger.info(json.dumps(fields, ensure_ascii=False))