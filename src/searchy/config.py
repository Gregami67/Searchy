import os
from pathlib import Path

DEBUG = True if os.getenv("DEBUG") == "true" else False
WATCHDOG = True if os.getenv("WATCHDOG") == "true" else False

BASE_DIR = Path(__file__).resolve().parents[2]

THUMB_DIR = BASE_DIR / "thumbs"
THUMB_DIR.mkdir(parents=True, exist_ok=True)

IMAGE_DIR = os.getenv("IMAGE_DIR")

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 32))
IMAGE_COUNT = int(os.getenv("IMAGE_COUNT", 50))
VALID_EXTENSIONS = set(os.getenv("VALID_EXTENSIONS", ".png, .jpg, .jpeg").split(", "))
