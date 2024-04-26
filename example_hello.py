import time
from pathlib import Path

from jobs import ImageOptions, JobOptions, ResourceOptions, SchedulingOptions, job


@job(
    options=JobOptions(
        image=ImageOptions(
            spec=Path("example-docker.yaml"),
            name="localhost:5000/hello-world-dev",
            tag="latest",
        ),
        resources=ResourceOptions(memory="4Gi", cpu="2"),
        scheduling=SchedulingOptions(
            priority_class="background", queue_name="user-queue"
        ),
    )
)
def hello_world():
    print("Hello, World!")
    time.sleep(10)
