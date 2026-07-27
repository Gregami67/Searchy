import valkey
from valkey.commands.search.field import VectorField, TagField
from valkey.commands.search.indexDefinition import IndexDefinition, IndexType

vk = valkey.Valkey()

fields = [
    TagField("url_path"),
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
    print("Created images index")
except valkey.ResponseError as e:
    if "already exists" in str(e).lower():
        print("Image index already exists... Skipping")
        pass
    else:
        raise e
