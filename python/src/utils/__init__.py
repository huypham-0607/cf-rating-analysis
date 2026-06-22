import logging
import sys
import json

from pathlib import Path

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger

def _load(dir: Path):
    try:
        with open(dir,'r') as f:
            data = json.load(f)
            return data
    except PermissionError as e:
        raise e
    except IsADirectoryError as e:
        raise e
    except FileNotFoundError as e:
        raise e

def _save(dir: Path, data)->None:
    try:
        with open(dir,'w') as f:
            f.write(json.dumps(data))
    except PermissionError:
        raise RuntimeError("Write Failed: No write permission.")
    except FileNotFoundError:
        raise RuntimeError("Write Failed: File not found.")
    except IsADirectoryError:
        raise RuntimeError("Write Failed: Invalid Directory.")