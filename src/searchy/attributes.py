import os
import logging

logger = logging.getLogger("searchy")

DEBUG = True if os.getenv("DEBUG") == "true" else False
WATCHDOG = True if os.getenv("WATCHDOG") == "true" else False

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 32))
IMAGE_COUNT = int(os.getenv("IMAGE_COUNT", 50))
IMAGE_DIR = os.getenv("IMAGE_DIR")
VALID_EXTENSIONS = set(os.getenv("VALID_EXTENSIONS", ".png, .jpg, .jpeg").split(", "))

if not IMAGE_DIR:
    raise ValueError("Environment variable 'IMAGE_DIR' is missing or not set.")

logger.info(
    f"Running with environment variables: BATCH_SIZE={BATCH_SIZE}, IMAGE_COUNT={IMAGE_COUNT}, IMAGE_DIR={IMAGE_DIR}, VALID_EXTENSIONS={VALID_EXTENSIONS}"
)
