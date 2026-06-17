import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
DEFAULT_LOG_FILE = "app.log"
DEFAULT_LOG_LEVEL = "INFO"
MAX_LOG_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
BACKUP_COUNT = 5

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_configured = False


def setup_logging(
    level: str | None = None,
    log_file: str = DEFAULT_LOG_FILE,
    log_to_console: bool = True,
    log_to_file: bool = True,
) -> None:
    """Configure application-wide logging. Call once at startup (e.g. in main)."""
    global _configured
    if _configured:
        return

    log_level = (level or os.getenv("LOG_LEVEL", DEFAULT_LOG_LEVEL)).upper()
    numeric_level = getattr(logging, log_level, logging.INFO)

    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()

    if log_to_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    if log_to_file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            LOG_DIR / log_file,
            maxBytes=MAX_LOG_SIZE_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a module logger. Use: logger = get_logger(__name__)"""
    return logging.getLogger(name)
