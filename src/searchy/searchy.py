import time
from pathlib import Path
from typing import Optional

import numpy as np
import torch
from PIL import Image
from torch.nn import functional as F
from transformers import CLIPModel, CLIPProcessor
from valkey.commands.search.query import Query
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

from searchy import db
from searchy.config import BATCH_SIZE, VALID_EXTENSIONS
from searchy.logging import logger
from searchy.tools import create_thumbs, delete_thumbs, get_images_to_update


class ImageFolderHandler(FileSystemEventHandler):
    def __init__(self, searchy: "Searchy", dir_path: Path):
        super().__init__()
        self.searchy = searchy
        self.dir_path = dir_path

    def _is_image(self, path: str) -> bool:
        return Path(path).suffix.lower() in VALID_EXTENSIONS

    def on_created(self, event: FileSystemEvent) -> None:
        if isinstance(event.src_path, bytes):
            logger.debug("Found bytes: {event.src_path}")
            return

        if not event.is_directory and self._is_image(event.src_path):
            logger.info(f"Detected new image: {event.src_path}")

            hash_paths_to_add, _ = get_images_to_update(self.searchy.vk, self.dir_path)
            hash_thumbs = create_thumbs(hash_paths_to_add)

            if len(hash_paths_to_add) != len(hash_thumbs):
                thumbs_set = hash_paths_to_add.keys() - hash_thumbs.keys()
                hash_paths_to_add = {h: hash_paths_to_add[h] for h in thumbs_set}

            embeds = self.searchy.create_embeds(list(hash_paths_to_add.values()))
            images_to_add = {
                hash: path.name for hash, path in hash_paths_to_add.items()
            }

            self.searchy.save_embeds(images_to_add, hash_thumbs, embeds)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if isinstance(event.src_path, bytes):
            logger.debug(f"Found bytes: {event.src_path}")
            return

        if not event.is_directory and self._is_image(event.src_path):
            logger.info(f"Detected deleted image: {event.src_path}")

            _, hash_names_to_delete = get_images_to_update(
                self.searchy.vk, self.dir_path
            )

            self.searchy.delete_embeds(list(hash_names_to_delete.keys()))
            delete_thumbs(list(hash_names_to_delete.values()))


class Searchy:
    def __init__(
        self,
        dir_path: Path,
        model_name: str = "openai/clip-vit-base-patch32",
        device: Optional[str] = None,
    ) -> None:
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.debug(f"Using: {device}")

        self.vk = db.vk
        self.model = CLIPModel.from_pretrained(model_name).to(device)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.device = device

        hash_paths_to_add, hash_names_to_delete = get_images_to_update(
            self.vk, dir_path
        )
        hash_thumbs = create_thumbs(hash_paths_to_add)

        if len(hash_paths_to_add) != len(hash_thumbs):
            logger.info("They are not the same size")
            thumbs_set = hash_paths_to_add.keys() - hash_thumbs.keys()
            hash_paths_to_add = {h: hash_paths_to_add[h] for h in thumbs_set}

        embeds = self.create_embeds(list(hash_paths_to_add.values()))
        images_to_add = {hash: path.name for hash, path in hash_paths_to_add.items()}

        self.save_embeds(images_to_add, hash_thumbs, embeds)
        self.delete_embeds(list(hash_names_to_delete.values()))

        logger.info("Searchy initialized")

    def create_embeds(self, paths: list[Path]) -> Optional[np.ndarray]:
        info = f"Found {len(paths)} image(s) to embed"

        if not paths:
            logger.info(info + "... Skipping")
            return None
        else:
            logger.info(info)

        all_embeds = []

        for i in range(0, len(paths), BATCH_SIZE):
            batch_paths = paths[i : i + BATCH_SIZE]
            batch_images = []

            for path in batch_paths:
                with Image.open(path) as img:
                    img = img.convert("RGB")
                    batch_images.append(img)

            inputs = self.processor(images=batch_images, return_tensors="pt").to(
                self.device
            )

            with torch.inference_mode():
                image_features = self.model.get_image_features(**inputs)
                embeds = image_features.pooler_output
                embeds_norm = F.normalize(embeds, dim=-1).cpu()

            all_embeds.append(embeds_norm)

        return torch.cat(all_embeds, dim=0).numpy().astype(np.float32)

    def save_embeds(
        self,
        images: dict[str, str],
        thumbs: dict[str, str],
        embeds: Optional[np.ndarray],
    ) -> None:
        info = f"Found {len(images)} embedding(s) to save"

        if not images or embeds is None:
            logger.info(info + "... Skipping")
            return None
        else:
            logger.info(info)

        if len(images) != len(thumbs):
            logger.error("Cannot perform embeds since image and thumbs are not equal")
            return None

        pipe = self.vk.pipeline()
        # TODO: Make tobytes here?

        for i, (hash, thumb_name) in enumerate(thumbs.items()):
            pipe.hset(
                f"image:{hash}",
                mapping={
                    "original_name": images[hash],
                    "thumb_name": thumb_name,
                    "embed": embeds[i].tobytes(),
                },
            )

        pipe.incrby("image_count", len(thumbs))
        pipe.execute()

    def delete_embeds(self, hashes: list[str]) -> None:
        info = f"Found {len(hashes)} embedding(s) to delete"

        if not hashes:
            logger.info(info + "... Skipping")
            return None
        else:
            logger.info(info)

        pipe = self.vk.pipeline()

        for hash in hashes:
            pipe.delete(f"image:{hash}")

        pipe.decrby("image_count", len(hashes))
        pipe.execute()

    def watch(self, image_dir: Path) -> None:
        event_handler = ImageFolderHandler(self, image_dir)
        observer = Observer()
        observer.schedule(event_handler, path=str(image_dir), recursive=False)
        observer.start()

        logger.info(f"Started watching directory: {image_dir}")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            logger.info("\nStopped watching directory.")
        observer.join()

    def _search_helper(self, page: int, count: int, vector_bytes: bytes):
        offset = (page - 1) * count
        k = offset + count

        search_query = (
            Query("*=>[KNN $k @embed $vec]")
            .paging(offset, count)
            .return_fields("original_name", "thumb_name")
        )

        results = self.vk.ft("idx:images").search(
            search_query,
            query_params={
                "k": k,
                "vec": vector_bytes,
            },
        )

        return results

    def search(
        self,
        page: int,
        count: int,
        query: Optional[str] = None,
        image: Optional[Image.Image] = None,
    ) -> tuple[list[str], list[str]]:
        logger.debug(f"Query to search is: {query}")

        if page <= 0:
            page = 1

        if bool(query) == bool(image):
            return [], []

        inputs = self.processor(
            images=image,
            text=query,
            return_tensors="pt",
        ).to(self.device)

        with torch.inference_mode():
            if query:
                features = self.model.get_text_features(**inputs)
            else:
                features = self.model.get_image_features(**inputs)

            embeds = (
                F.normalize(features.pooler_output, dim=-1)
                .squeeze(0)
                .cpu()
                .numpy()
                .astype(np.float32)
            )

        vector_bytes = embeds.tobytes()
        results = self._search_helper(page, count, vector_bytes)

        return [result.original_name for result in results.docs], [
            result.thumb_name for result in results.docs
        ]

    def search_name(
        self, page: int, count: int, name: str
    ) -> tuple[list[str], list[str]]:
        logger.debug(f"Name to search is:{name}")

        query = Query(f"@thumb_name:{{{name}}}").no_content()
        result = self.vk.ft("idx:images").search(query)

        if not result.docs:
            return [], []

        image_hash = result.docs[0].id
        vector_bytes = self.vk.hget(image_hash, "embed")

        if not vector_bytes:
            return [], []

        results = self._search_helper(page, count, vector_bytes)

        return [result.original_name for result in results.docs], [
            result.thumb_name for result in results.docs
        ]
