# -*- coding: utf-8 -*-
"""
Structured Logging — Replaces all print() statements.
Logs to console AND rotating file for cloud debugging.
"""

import os
import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "agency.log")

# Shared formatter
_FMT = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-7s | %(name)-18s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger with both console and file handlers.
    File rotates at 5 MB, keeps 3 backups.
    """
    logger = logging.getLogger(f"agency.{name}")

    if logger.handlers:
        return logger  # Already configured

    logger.setLevel(logging.DEBUG)

    # Console handler (INFO+)
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(_FMT)
    logger.addHandler(ch)

    # File handler (DEBUG+ with rotation)
    fh = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3, encoding='utf-8')
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(_FMT)
    logger.addHandler(fh)

    return logger
