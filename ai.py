from searchy import Searchy
from searchy.tools import tools


def main():
    searchy = Searchy(device="cpu")

    paths = tools.get_image_paths()
    hashes = tools.get_image_hashes(paths)
    images_to_add, hashes_to_delete = tools.get_images_to_update(
        vk=searchy.vk,
        paths=paths,
        hashes=hashes,
    )
    paths = [p for _, p in images_to_add]
    embeds = searchy.create_embeds(paths)

    if embeds is not None:
        searchy.save_embeds(images_to_add, embeds)

    print(searchy.search("blue hair", 50))


if __name__ == "__main__":
    main()
