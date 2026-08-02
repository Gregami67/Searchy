import os
import logging
from pathlib import Path

logger = logging.getLogger("searchy")

DEBUG = True if os.getenv("DEBUG") == "true" else False
WATCHDOG = True if os.getenv("WATCHDOG") == "true" else False

BASE_DIR = Path(__file__).resolve().parents[2]
THUMB_DIR = BASE_DIR / "thumbs"
IMAGE_DIR = os.getenv("IMAGE_DIR")

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 32))
IMAGE_COUNT = int(os.getenv("IMAGE_COUNT", 50))
VALID_EXTENSIONS = set(os.getenv("VALID_EXTENSIONS", ".png, .jpg, .jpeg").split(", "))

if not IMAGE_DIR:
    raise ValueError("Environment variable 'IMAGE_DIR' is missing or not set.")

logger.info(
    f"Running with environment variables: BATCH_SIZE={BATCH_SIZE}, IMAGE_COUNT={IMAGE_COUNT}, IMAGE_DIR={IMAGE_DIR}, VALID_EXTENSIONS={VALID_EXTENSIONS}"
)
