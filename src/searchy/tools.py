import hashlib
import uuid
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from typing import Optional

import valkey
from PIL import Image, UnidentifiedImageError

from searchy.config import THUMB_DIR, VALID_EXTENSIONS
from searchy.logging import logger


def get_paths(dir_path: Path) -> list[Path]:
    if not dir_path.is_dir():
        raise FileNotFoundError(f"Directory '{dir_path}' does not exist")

    return sorted(
        [
            p
            for p in dir_path.iterdir()
            if p.is_file() and p.suffix.lower() in VALID_EXTENSIONS
        ]
    )


def _get_hash_path(image_path: Path) -> tuple[Optional[str], Path]:
    try:
        with open(image_path, "rb") as f:
            return hashlib.file_digest(f, "sha256").hexdigest(), image_path
    except FileNotFoundError as e:
        logger.error(f"Cannot read image '{image_path}': {e}")
        return None, image_path


def get_hash_paths(image_paths: list[Path]) -> dict[str, Path]:
    with ThreadPoolExecutor() as executor:
        return {h: p for h, p in executor.map(_get_hash_path, image_paths) if h}


def _create_thumb(hash_path: tuple[str, Path]) -> tuple[Optional[str], str]:
    name = str(uuid.uuid4())
    save_path = THUMB_DIR / f"{name}.jpg"
    hash, path = hash_path

    try:
        with Image.open(path) as img:
            img = img.convert("RGB")

            img.thumbnail((256, 256))
            img.save(save_path, "JPEG", quality=75)

            return hash, save_path.name
    except UnidentifiedImageError as e:
        logger.error(f"Cannot create thumb for '{path}': {e}")
        return None, save_path.name


def create_thumbs(hash_paths: dict[str, Path]) -> dict[str, str]:
    with ProcessPoolExecutor() as executor:
        thumb_hashes = {
            h: n for h, n in executor.map(_create_thumb, hash_paths.items()) if h
        }

    return thumb_hashes


def delete_thumbs(thumb_names: list[str]) -> None:
    for name in thumb_names:
        thumb_path = THUMB_DIR / name
        thumb_path.unlink()


def get_images_to_update(
    vk: valkey.Valkey,
    dir_path: Path,
) -> tuple[dict[str, Path], dict[str, str]]:
    paths = get_paths(dir_path)
    hash_paths = get_hash_paths(paths)
    input_hashes = set(hash_paths.keys())

    vk_keys = {key.decode() for key in vk.scan_iter("image:*")}
    vk_hashes = {key.removeprefix("image:") for key in vk_keys}

    hashes_to_add = list(input_hashes - vk_hashes)
    hashes_to_delete = list(vk_hashes - input_hashes)

    pipe = vk.pipeline()

    for hash in hashes_to_delete:
        pipe.hget(f"image:{hash}", "thumb_name")

    vk_thumb_names = pipe.execute()
    vk_hash_paths = dict(zip(hashes_to_delete, vk_thumb_names))

    images_to_add = {h: hash_paths[h] for h in hashes_to_add}
    images_to_delete = {h: p.decode() for h, p in vk_hash_paths.items()}

    return images_to_add, images_to_delete
