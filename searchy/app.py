from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
from valkey.commands.search.query import Query

import db


class Searchy:
    def __init__(
        self,
        model_name: str = "openai/clip-vit-base-patch32",
        device: str | None = None,
    ) -> None:
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.vk = db.vk
        self.model = CLIPModel.from_pretrained(model_name).to(device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.device = device

    def create_embeds(
        self, image_paths: list[Path], batch_size=32
    ) -> torch.Tensor | None:
        print(f"Found {len(image_paths)} image(s) to embed", end="")

        if len(image_paths) == 0:
            print("... Skipping")
            return None
        else:
            print()

        all_embeds = []

        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i : i + batch_size]
            batch_images = []

            for path in batch_paths:
                with Image.open(path) as img:
                    batch_images.append(img.convert("RGB"))

            inputs = self.processor(images=batch_images, return_tensors="pt")

            with torch.inference_mode():
                image_features = self.model.get_image_features(**inputs)

            embeds = image_features.pooler_output
            embeds_norm = torch.nn.functional.normalize(embeds, dim=-1)
            all_embeds.append(embeds_norm.cpu())

        return torch.cat(all_embeds, dim=0)

    def save_embeds(
        self,
        images: list[tuple[str, Path]],
        embeds: torch.Tensor | None,
    ) -> None:
        print(f"Found {len(images)} embedding(s) to save", end="")

        if len(images) == 0 or embeds is None:
            print("... Skipping")
            return None
        else:
            print()

        pipe = self.vk.pipeline()
        embeds_np = embeds.detach().cpu().numpy().astype(np.float32)

        for image, embed in zip(images, embeds_np):
            hash, path = image

            pipe.hset(
                f"image:{hash}",
                mapping={"url_path": str(path), "image_embed": embed.tobytes()},
            )

        pipe.incrby("image_count", len(images))
        pipe.execute()

    def delete_embeds(self, hashes: list[str]) -> None:
        print(f"Found {len(hashes)} embedding(s) to delete", end="")

        if len(hashes) == 0:
            print("... Skipping")
            return None
        else:
            print()

        pipe = self.vk.pipeline()

        for hash in hashes:
            pipe.delete(f"image:{hash}")

        pipe.decrby("image_count", len(hashes))
        pipe.execute()

    def search(
        self,
        query: str,
        page: int,
        count: int = 50,
    ) -> list[str]:
        if page <= 0:
            page = 1

        inputs = self.processor(text=[query], return_tensors="pt")

        with torch.inference_mode():
            text_features = self.model.get_text_features(**inputs)

        text_embeds = (
            torch.nn.functional.normalize(text_features.pooler_output, dim=-1)
            .squeeze(0)
            .cpu()
            .numpy()
            .astype(np.float32)
        )

        query_vector_bytes = text_embeds.tobytes()
        num_images = self.vk.get("image_count").decode()
        page_size = count * page
        search_query = (
            Query(f"*=>[KNN {num_images} @image_embed $vec AS vector_distance]")
            .paging(page_size - count, page_size)
            .return_fields("url_path", "vector_distance")
        )

        results = self.vk.ft("idx:images").search(
            search_query, query_params={"vec": query_vector_bytes}
        )

        return [result.url_path for result in results.docs]
