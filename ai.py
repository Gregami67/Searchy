import argparse
import os
import sys

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
from valkey.commands.search.query import Query

from db import v

EMBEDDINGS_FILE = "embeddings.json"


def load_model_and_processor(device=None):
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
    processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

    return model, processor, device


def write_embeddings_to_db(paths, embeds):
    pipe = v.pipeline()
    embeds_np = embeds.detach().cpu().numpy().astype(np.float32)
    end_id = v.incrby("image_counter", len(paths))
    start_id = end_id - len(paths) + 1

    for i, (p, e) in enumerate(zip(paths, embeds_np)):
        img_id = start_id + i

        pipe.hset(
            f"image:{img_id}",
            mapping={
                "url_path": p,
                "image_embed": e.tobytes(),
            },
        )

    pipe.execute()


def vectorize_batch(image_paths, processor, model, device, batch_size=32):
    """Vectorize images in batches and ensure file handles are properly closed."""
    all_embeds = []

    for i in range(0, len(image_paths), batch_size):
        batch_paths = image_paths[i : i + batch_size]
        batch_images = []

        for path in batch_paths:
            with Image.open(path) as img:
                # convert("RGB") loads image data immediately into memory and strips transparency
                batch_images.append(img.convert("RGB"))

        inputs = processor(images=batch_images, return_tensors="pt")
        pixel_values = inputs["pixel_values"].to(device)

        with torch.inference_mode():
            outputs = model.get_image_features(pixel_values=pixel_values)

        embeds = outputs.pooler_output
        embeds = torch.nn.functional.normalize(embeds, dim=-1)
        all_embeds.append(embeds.cpu())

    return torch.cat(all_embeds, dim=0)


def get_image_paths(image_dir="./images"):
    valid_extensions = (".png", ".jpg", ".jpeg", ".webp", ".bmp")

    if not os.path.exists(image_dir):
        print(f"Error: Image directory '{image_dir}' does not exist.")
        sys.exit(1)

    return sorted(
        [
            os.path.join(image_dir, f)
            for f in os.listdir(image_dir)
            if f.lower().endswith(valid_extensions)
        ]
    )


def search_embeddings_db(query, processor, model, device) -> None:
    inputs = processor(text=[query], return_tensors="pt")

    with torch.inference_mode():
        outputs = model.get_text_features(
            input_ids=inputs["input_ids"].to(device),
            attention_mask=inputs["attention_mask"].to(device),
        )

    text_embeds = (
        torch.nn.functional.normalize(outputs.pooler_output, dim=-1)
        .squeeze(0)
        .cpu()
        .numpy()
        .astype(np.float32)
    )

    query_vector_bytes = text_embeds.tobytes()
    raw_count = v.get("image_counter")

    if not raw_count:
        return None

    num_images = int(raw_count)

    search_query = (
        Query(f"*=>[KNN {num_images} @image_embed $vec AS vector_distance]")
        .paging(0, num_images)
        .return_fields("url_path", "vector_distance")
    )

    results = v.ft("idx:images").search(
        search_query, query_params={"vec": query_vector_bytes}
    )

    return [result.url_path for result in results.docs]


def main():
    parser = argparse.ArgumentParser(
        description="CLIP-based image search and vectorization"
    )
    parser.add_argument(
        "action",
        choices=["vectorize", "search"],
        help="Action to perform: vectorize images or search by query",
    )
    parser.add_argument(
        "--query",
        type=str,
        default=None,
        help="Search query text (required for 'search' action)",
    )
    parser.add_argument(
        "--image-dir",
        type=str,
        default="./images",
        help="Directory containing images (used only for 'vectorize')",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for vectorizing images",
    )

    args = parser.parse_args()

    if not os.path.exists(EMBEDDINGS_FILE) and args.action == "search":
        print(
            f"Error: '{EMBEDDINGS_FILE}' not found. Run 'vectorize' first to generate embeddings."
        )
        sys.exit(1)

    model, processor, device = load_model_and_processor("cpu")

    if args.action == "vectorize":
        image_paths = get_image_paths(args.image_dir)
        if not image_paths:
            print(f"No valid images found in '{args.image_dir}'.")
            sys.exit(0)

        print(f"Vectorizing {len(image_paths)} images...")
        image_embeds = vectorize_batch(
            image_paths, processor, model, device, batch_size=args.batch_size
        )

        write_embeddings_to_db(image_paths, image_embeds)
        print(f"Saved {len(image_paths)} embeddings to '{EMBEDDINGS_FILE}'.")

    elif args.action == "search":
        if not args.query:
            print("Error: --query is required for 'search' action.")
            sys.exit(1)

        results = search_embeddings_db(args.query, processor, model, device)
        print(results)

        # print("feh ", *[path for path, _ in results[:25]])


if __name__ == "__main__":
    main()
