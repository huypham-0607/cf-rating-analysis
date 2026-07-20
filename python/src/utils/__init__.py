"""
Shared utilities: project root path, logger factory, and JSON loader.
"""
import json
import logging
import sys

from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def _load(path: Path) -> list | dict:
    """Load and return parsed JSON from path; raises on any IO or parse error."""
    with open(path, "r") as f:
        return json.load(f)
