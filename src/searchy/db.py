import os

import valkey
from valkey.commands.search.field import TagField, VectorField
from valkey.commands.search.indexDefinition import IndexDefinition, IndexType

from searchy.logging import logger

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
    vk.execute_command("FT.DROPINDEX", "idx:images")
    logger.info("Dropped existing images index to rebuild vector index")
except valkey.ResponseError:
    pass

vk.ft("idx:images").create_index(
    fields=fields,
    definition=IndexDefinition(
        ["image:"],
        index_type=IndexType.HASH,
    ),
)
