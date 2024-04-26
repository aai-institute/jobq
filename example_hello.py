import logging
import time
from pathlib import Path

from jobs import ImageOptions, JobOptions, ResourceOptions, SchedulingOptions, job
from jobs.cli import submit_job


@job(
    options=JobOptions(
        # A job with explicit Dockerfile
        image=ImageOptions(
            dockerfile=Path("Dockerfile"),
            name="hello-world-dev",
            tag="latest",
        ),
        resources=ResourceOptions(memory="256Mi", cpu="1"),
        scheduling=SchedulingOptions(
            priority_class="background",
        ),
    )
)
def hello_world():
    print("Hello, World!")
    time.sleep(60)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

    submit_job(hello_world)
