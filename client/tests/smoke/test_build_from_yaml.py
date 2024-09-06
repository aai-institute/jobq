from pathlib import Path

from jobs import assembler
from jobs.job import ImageOptions, Job, JobOptions, ResourceOptions


def test_build_image_from_yaml():
    testjob = Job(
        func=lambda: print("Ran test"),
        options=JobOptions(
            labels={"job-type": "test"},
            resources=ResourceOptions(),
        ),
        image=ImageOptions(
            spec=Path("_data/docker.yaml"),
            name="pytest-example",
            tag="test",
        ),
    )
    testjob._render_dockerfile()


def test_image_assembler():
    _ = assembler.load_config(Path("tests/smoke/_data/docker.yaml"))
