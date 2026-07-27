import hashlib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import valkey

from searchy.app import Searchy


def _get_image_paths(image_dir: str) -> list[Path]:
    path = Path(image_dir)

    if not path.exists():
        raise FileNotFoundError(f"Image directory '{path}' does not exist.")

    return sorted(
        [
            p
            for p in path.iterdir()
            if p.is_file() and p.suffix.lower() in Searchy.VALID_EXTENSIONS
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


def get_images_to_update(
    vk: valkey.Valkey,
    image_dir: str,
) -> tuple[list[tuple[str, Path]], list[str]]:
    paths = _get_image_paths(image_dir)
    hashes = _get_image_hashes(paths)
    images = dict(zip(hashes, paths))
    input_hashes = set(hashes)

    vk_keys = {key.decode() for key in vk.scan_iter("image:*")}
    vk_hashes = {key.removeprefix("image:") for key in vk_keys}

    add_set = input_hashes - vk_hashes
    delete_set = vk_hashes - input_hashes

    images_to_add = [(hash, images[hash]) for hash in add_set]
    hashes_to_delete = [hash for hash in delete_set]

    return images_to_add, hashes_to_delete
