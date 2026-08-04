import logging

from flask.logging import default_handler

from searchy.config import DEBUG

logger = logging.getLogger("searchy")
logger.setLevel(logging.DEBUG if DEBUG else logging.INFO)
logger.addHandler(default_handler)
