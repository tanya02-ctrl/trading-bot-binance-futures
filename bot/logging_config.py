"""
Logging configuration for the trading bot.
Writes structured logs to both console and a rotating log file.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
LOG_FILE = os.path.join(LOG_DIR, "trading_bot.log")

_configured = False


def setup_logging(level: int = logging.DEBUG) -> logging.Logger:
    """
    Set up and return the root logger for the bot.
    Safe to call multiple times — configures only once.
    """
    global _configured
    if _configured:
        return logging.getLogger("trading_bot")

    os.makedirs(LOG_DIR, exist_ok=True)

    fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt, datefmt=datefmt)

    # File handler — keeps last 5 × 2 MB = 10 MB of history
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Console handler — INFO and above only (keeps terminal clean)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    root = logging.getLogger("trading_bot")
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
    root.propagate = False

    _configured = True
    return root


def get_logger(name: str) -> logging.Logger:
    """Return a child logger; call setup_logging() first."""
    return logging.getLogger(f"trading_bot.{name}")
