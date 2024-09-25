from pathlib import Path

from jobq import assembler
from jobq.job import ImageOptions, Job, JobOptions, ResourceOptions, SchedulingOptions


def test_build_image_from_yaml():
    testjob = Job(
        func=lambda: print("Ran test"),
        options=JobOptions(
            labels={"job-type": "test"},
            resources=ResourceOptions(),
            scheduling=SchedulingOptions(queue_name="q"),
        ),
        image=ImageOptions(
            spec=Path("tests/smoke/_data/docker.yaml"),
            name="pytest-example",
            tag="test",
        ),
    )
    testjob._render_dockerfile()


def test_image_assembler():
    _ = assembler.load_config(Path("tests/smoke/_data/docker.yaml"))
