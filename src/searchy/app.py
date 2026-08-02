import logging
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.nn import functional as F
from transformers import CLIPModel, CLIPProcessor
from valkey.commands.search.query import Query
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

import db
from searchy.attributes import BATCH_SIZE, VALID_EXTENSIONS
from searchy.tools import delete_image_thumbs, get_images_to_update, create_image_thumbs

logger = logging.getLogger("searchy")


class ImageFolderHandler(FileSystemEventHandler):
    def __init__(self, searchy: "Searchy", image_dir: str):
        super().__init__()
        self.searchy = searchy
        self.image_dir = image_dir

    def _is_image(self, path_str: str) -> bool:
        return Path(path_str).suffix.lower() in VALID_EXTENSIONS

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_image(event.src_path):
            logger.info(f"Detected new image: {event.src_path}")

            (hashes, paths), _ = get_images_to_update(self.searchy.vk, self.image_dir)
            create_image_thumbs(paths)
            embeds = self.searchy.create_embeds(paths)
            images = [(hash, path.stem) for hash, path in zip(hashes, paths)]

            self.searchy.save_embeds(images, embeds)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory and self._is_image(event.src_path):
            logger.info(f"Detected deleted image: {event.src_path}")

            delete_image_thumbs([Path(str(event.src_path))])
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

        create_image_thumbs(paths)

        embeds = self.create_embeds(paths)
        images_to_add = [(hash, path.stem) for hash, path in zip(hashes, paths)]

        self.save_embeds(images_to_add, embeds)
        self.delete_embeds(hashes_to_delete)

        logger.info("Searchy initialized")

    def create_embeds(self, image_paths: list[Path]) -> np.ndarray | None:
        info = f"Found {len(image_paths)} image(s) to embed"

        if not image_paths:
            logger.info(info + "... Skipping")
            return None
        else:
            logger.info(info)

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
                embeds_norm = F.normalize(embeds, dim=-1).cpu()

            all_embeds.append(embeds_norm)

        return torch.cat(all_embeds, dim=0).numpy().astype(np.float32)

    def save_embeds(
        self,
        images: list[tuple[str, str]],
        embeds: np.ndarray | None,
    ) -> None:
        info = f"Found {len(images)} embedding(s) to save"

        if not images or embeds is None:
            logger.info(info + "... Skipping")
            return None
        else:
            logger.info(info)

        pipe = self.vk.pipeline()
        # TODO: Make tobytes here?

        for image, embed in zip(images, embeds):
            hash, name = image

            pipe.hset(
                f"image:{hash}",
                mapping={"name": name, "image_embed": embed.tobytes()},
            )

        pipe.incrby("image_count", len(images))
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

    def watch(self, image_dir: str) -> None:
        event_handler = ImageFolderHandler(self, image_dir)
        observer = Observer()
        observer.schedule(event_handler, path=image_dir, recursive=False)
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
            Query("*=>[KNN $k @image_embed $vec]")
            .paging(offset, count)
            .return_fields("name")
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
        query: str | None = None,
        image: Image.Image | None = None,
    ) -> list[str]:
        logger.debug(f"Query to search is: {query}")

        if page <= 0:
            page = 1

        if bool(query) == bool(image):
            return []

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

        return [result.name for result in results.docs]

    def search_name(self, page: int, count: int, name: str) -> list[str]:
        logger.debug(f"Name to search is:{name}")

        query = Query(f"@name:{{{name}}}").no_content()
        result = self.vk.ft("idx:images").search(query)

        if not result.docs:
            return []

        image_hash = result.docs[0].id
        vector_bytes = self.vk.hget(image_hash, "image_embed")

        if not vector_bytes:
            return []

        results = self._search_helper(page, count, vector_bytes)

        return [result.name for result in results.docs]
