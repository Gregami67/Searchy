import hashlib
import logging
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

import valkey
from PIL import Image

from searchy.attributes import THUMB_DIR, VALID_EXTENSIONS

logger = logging.getLogger("searchy")


def _get_image_paths(image_dir: str) -> list[Path]:
    path = Path(image_dir)

    if not path.exists():
        raise FileNotFoundError(f"Image directory '{path}' does not exist.")

    return sorted(
        [
            p
            for p in path.iterdir()
            if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS
        ]
    )


def _get_image_hashes(image_paths: list[Path]) -> list[str]:
    def get_image_hash(path: str) -> str:
        hasher = hashlib.sha256()

        with open(path, "rb") as f:
            while chunk := f.read(1024 * 512):
                hasher.update(chunk)

        return hasher.hexdigest()

    with ThreadPoolExecutor() as executor:
        return list(executor.map(get_image_hash, image_paths))


def _create_image_thumb(path: Path) -> None:
    with Image.open(path) as img:
        save_path = THUMB_DIR / f"{path.stem}.jpg"

        if img.mode in ("RGBA", "P", "LA") or (
            img.mode == "M" and "transparency" in img.info
        ):
            img = img.convert("RGB")

        img.thumbnail((512, 512))
        img.save(save_path, "JPEG", quality=75)


def create_image_thumbs(image_paths: list[Path]) -> None:
    logger.info(f"Created {len(image_paths)} of thumbnails")
    with ProcessPoolExecutor() as executor:
        executor.map(_create_image_thumb, image_paths)


def delete_image_thumbs(image_paths: list[Path]):
    for image_path in image_paths:
        thumb_path = THUMB_DIR / f"{image_path.stem}.jpg"
        logger.info(f"Deleted {len(image_paths)} of thumbnails")

        thumb_path.unlink(missing_ok=True)


def get_images_to_update(
    vk: valkey.Valkey,
    image_dir: str,
) -> tuple[tuple[list[str], list[Path]], list[str]]:
    paths = _get_image_paths(image_dir)
    hashes = _get_image_hashes(paths)
    images = dict(zip(hashes, paths))
    input_hashes = set(hashes)

    vk_keys = {key.decode() for key in vk.scan_iter("image:*")}
    vk_hashes = {key.removeprefix("image:") for key in vk_keys}

    add_set = input_hashes - vk_hashes
    delete_set = vk_hashes - input_hashes

    hashes_to_add = [hash for hash in add_set]
    paths_to_add = [images[hash] for hash in add_set]

    images_to_add = hashes_to_add, paths_to_add
    hashes_to_delete = [hash for hash in delete_set]

    return images_to_add, hashes_to_delete
