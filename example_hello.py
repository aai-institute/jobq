import time
from pathlib import Path

from jobs import ImageOptions, JobOptions, ResourceOptions, SchedulingOptions, job


@job(
    options=JobOptions(
        labels={"type": "hello-world@dev", "x-jobby.io/key": "value"},
        image=ImageOptions(
            spec=Path("example-docker.yaml"),
            name="localhost:5000/hello-world-dev",
            tag="latest",
        ),
        resources=ResourceOptions(memory="1Gi", cpu="1"),
        scheduling=SchedulingOptions(
            priority_class="background", queue_name="user-queue"
        ),
    )
)
def hello_world():
    print("Hello, World!")
    time.sleep(10)
