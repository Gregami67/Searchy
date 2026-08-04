import logging
import os

import valkey
from valkey.commands.search.field import TagField, VectorField
from valkey.commands.search.indexDefinition import IndexDefinition, IndexType

logger = logging.getLogger("searchy")
vk = valkey.Valkey(os.getenv("VALKEY_HOST", "localhost"))

fields = [
    TagField("original_name"),
    TagField("thumb_name"),
    VectorField(
        "embed",
        "FLAT",
        {"DIM": 512, "TYPE": "FLOAT32", "DISTANCE_METRIC": "COSINE"},
    ),
]

try:
    vk.ft("idx:images").create_index(
        fields=fields,
        definition=IndexDefinition(
            ["image:"],
            index_type=IndexType.HASH,
        ),
    )
    logger.info("Created images index")
except valkey.ResponseError as e:
    if "already exists" in str(e).lower():
        logger.info("Image index already exists... Skipping")
        pass
    else:
        raise e
