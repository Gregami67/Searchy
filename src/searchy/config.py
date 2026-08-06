import os
from pathlib import Path

DEBUG = True if os.getenv("DEBUG") == "true" else False
WATCHDOG = True if os.getenv("WATCHDOG") == "true" else False

IMAGE_DIR = os.getenv("IMAGE_DIR", None)
THUMB_DIR = os.getenv("THUMB_DIR", None)

if not IMAGE_DIR:
    raise ValueError("Environment variable 'IMAGE_DIR' is missing or not set")

if not THUMB_DIR:
    raise ValueError("Environment variable 'THUMB_DIR' is missing or not set")

IMAGE_DIR = Path(IMAGE_DIR)
THUMB_DIR = Path(THUMB_DIR)

THUMB_DIR.mkdir(exist_ok=True)

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 32))
IMAGE_COUNT = int(os.getenv("IMAGE_COUNT", 50))
VALID_EXTENSIONS = set(os.getenv("VALID_EXTENSIONS", ".png, .jpg, .jpeg").split(", "))
