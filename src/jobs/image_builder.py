import docker

from jobs import Image

WORKING_DIRECTORY = "."


class ImageBuilder:

    @staticmethod
    def from_dockerfile(tag: str) -> Image:
        client = docker.from_env()

        client.images.build(
            tag=tag,
            path=WORKING_DIRECTORY,
        )

        return Image(tag)
