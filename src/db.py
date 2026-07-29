import valkey
import logging
from valkey.commands.search.field import VectorField, TagField
from valkey.commands.search.indexDefinition import IndexDefinition, IndexType

logger = logging.getLogger("searchy")
vk = valkey.Valkey()

fields = [
    TagField("name"),
    VectorField(
        "image_embed",
        "FLAT",
        {"DIM": 512, "TYPE": "FLOAT32", "DISTANCE_METRIC": "COSINE"},
    ),
]

try:
    vk.ft("idx:images").create_index(
        fields=fields, definition=IndexDefinition(["image:"], index_type=IndexType.HASH)
    )
    logger.info("Created images index")
except valkey.ResponseError as e:
    if "already exists" in str(e).lower():
        logger.info("Image index already exists... Skipping")
        pass
    else:
        raise e
