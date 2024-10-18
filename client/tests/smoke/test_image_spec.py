import re
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
    dockerfile = testjob._render_dockerfile()

    # Base image
    pattern = r"FROM python:3.12-slim"
    assert (
        re.search(pattern, dockerfile) is not None
    ), "Base image not found or incorrect"

    # Wheel installation
    pattern = r"RUN .* pip install.*test\.whl"
    assert re.search(pattern, dockerfile) is not None, "Wheel installation not found"

    # Editable package install
    pattern = r"RUN .* pip install.*-e[ ]?[.]"
    assert (
        re.search(pattern, dockerfile) is not None
    ), "Editable package installation not found"

    # Regular package install
    pattern = r"RUN .* pip install.*marker-package"
    assert (
        re.search(pattern, dockerfile) is not None
    ), "Marker package installation not found"

    # Labels
    pattern = r"LABEL FOO=bar"
    assert re.search(pattern, dockerfile) is not None, "Label not found"

    # Build args
    pattern = r"ARG ARG=value"
    assert re.search(pattern, dockerfile) is not None, "Build arg not found"


def test_image_assembler():
    _ = assembler.load_config(Path("tests/smoke/_data/docker.yaml"))
