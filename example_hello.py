import logging
import time

from jobs import ImageOptions, JobOptions, ResourceOptions, SchedulingOptions, job
from jobs.cli import submit_job


@job(
    options=JobOptions(
        image=ImageOptions(
            spec="example-docker.yaml",
            name="mlops:5000/hello-world-dev",
            tag="latest",
        ),
        resources=ResourceOptions(memory="4Gi", cpu="4"),
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
