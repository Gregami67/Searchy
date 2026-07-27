from searchy import Searchy
from searchy.tools import tools


def main():
    searchy = Searchy(device="cpu")
    images_to_add, hashes_to_delete = tools.get_images_to_update(vk=searchy.vk)
    paths = [p for _, p in images_to_add]
    embeds = searchy.create_embeds(paths)

    searchy.save_embeds(images_to_add, embeds)
    searchy.delete_embeds(hashes_to_delete)

    print(searchy.search("potato", page=1))


if __name__ == "__main__":
    main()
