import logging

from jobs import ImageOptions, JobOptions, ResourceOptions, job
from jobs.cli import submit_job


@job(
    options=JobOptions(
        # A job with explicit Dockerfile
        image=ImageOptions(
            dockerfile="Dockerfile",
            name="hello-world-yaml",
            tag="latest",
        ),
        resources=ResourceOptions(memory="2Gi", cpu="1", gpu=None),
    )
)
def hello_world():
    print("Hello, World!")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

    submit_job(hello_world)
