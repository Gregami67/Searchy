import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor
from valkey.commands.search.query import Query
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

import db
from searchy.attributes import BATCH_SIZE, VALID_EXTENSIONS
from searchy.tools import get_images_to_update


class ImageFolderHandler(FileSystemEventHandler):
    def __init__(self, searchy: "Searchy", image_dir: str):
        super().__init__()
        self.searchy = searchy
        self.image_dir = image_dir

    def _is_image(self, path_str: str) -> bool:
        return Path(path_str).suffix.lower() in VALID_EXTENSIONS

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_image(event.src_path):
            print(f"Detected new image: {event.src_path}")

            (hashes, paths), _ = get_images_to_update(self.searchy.vk, self.image_dir)
            embeds = self.searchy.create_embeds(paths)
            images = [(hash, path.name) for hash, path in zip(hashes, paths)]

            self.searchy.save_embeds(images, embeds)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_image(event.src_path):
            print(f"Detected deleted image: {event.src_path}")

            _, hashes = get_images_to_update(self.searchy.vk, self.image_dir)
            self.searchy.delete_embeds(hashes)


class Searchy:
    def __init__(
        self,
        image_dir: str,
        model_name: str = "openai/clip-vit-base-patch32",
        device: str | None = None,
    ) -> None:
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.vk = db.vk
        self.model = CLIPModel.from_pretrained(model_name).to(device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.device = device

        (hashes, paths), hashes_to_delete = get_images_to_update(
            vk=self.vk,
            image_dir=image_dir,
        )
        embeds = self.create_embeds(paths)
        images_to_add = [(hash, path.name) for hash, path in zip(hashes, paths)]

        self.save_embeds(images_to_add, embeds)
        self.delete_embeds(hashes_to_delete)

        print("Searchy initialized")

    def create_embeds(self, image_paths: list[Path]) -> torch.Tensor | None:
        print(f"Found {len(image_paths)} image(s) to embed", end="")

        if len(image_paths) == 0:
            print("... Skipping")
            return None
        else:
            print()

        all_embeds = []

        for i in range(0, len(image_paths), BATCH_SIZE):
            batch_paths = image_paths[i : i + BATCH_SIZE]
            batch_images = []

            for path in batch_paths:
                with Image.open(path) as img:
                    batch_images.append(img.convert("RGB"))

            inputs = self.processor(images=batch_images, return_tensors="pt").to(
                self.device
            )

            with torch.inference_mode():
                image_features = self.model.get_image_features(**inputs)

            embeds = image_features.pooler_output
            embeds_norm = torch.nn.functional.normalize(embeds, dim=-1)
            all_embeds.append(embeds_norm.cpu())

        return torch.cat(all_embeds, dim=0)

    def save_embeds(
        self,
        images: list[tuple[str, str]],
        embeds: torch.Tensor | None,
    ) -> None:
        print(f"Found {len(images)} embedding(s) to save", end="")

        if len(images) == 0 or embeds is None:
            print("... Skipping")
            return None
        else:
            print()

        pipe = self.vk.pipeline()
        # TODO: Make tobytes here?
        embeds_np = embeds.detach().cpu().numpy().astype(np.float32)

        for image, embed in zip(images, embeds_np):
            hash, name = image

            pipe.hset(
                f"image:{hash}",
                mapping={"name": name, "image_embed": embed.tobytes()},
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

    def watch(self, image_dir: str) -> None:
        event_handler = ImageFolderHandler(self, image_dir)
        observer = Observer()
        observer.schedule(event_handler, path=image_dir, recursive=False)
        observer.start()

        print(f"Started watching directory: {image_dir}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            print("\nStopped watching directory.")
        observer.join()

    def search(
        self,
        query: str,
        page: int,
        count: int,
    ) -> list[str]:
        print(f"Query to search is: {query}")

        if page <= 0:
            page = 1

        inputs = self.processor(text=[query], return_tensors="pt").to(self.device)

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
        num_images = self.vk.get("image_count")
        num_images = int(num_images.decode()) if num_images else 1
        num_images = 1 if num_images == 0 else num_images

        page_size = count * page
        search_query = (
            Query(f"*=>[KNN {num_images} @image_embed $vec AS vector_distance]")
            .paging(page_size - count, page_size)
            .return_fields("name", "vector_distance")
        )

        results = self.vk.ft("idx:images").search(
            search_query, query_params={"vec": query_vector_bytes}
        )

        return [result.name for result in results.docs]
