from pathlib import Path

from jobs import assembler
from jobs.job import ImageOptions, Job, JobOptions, ResourceOptions


def test_build_image_from_yaml():
    testjob = Job(
        func=lambda: print("Ran test"),
        options=JobOptions(
            resources=ResourceOptions(),
            image=ImageOptions(
                spec=Path("tests/smoke/_data/docker.yaml"),
                name="pytest-example",
                tag="test",
            ),
        ),
    )
    testjob._image_from_yaml()


def test_image_assembler():
    config = assembler.load_config(Path("tests/smoke/_data/docker.yaml"))
