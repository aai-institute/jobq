import time
from pathlib import Path

from jobq import ImageOptions, JobOptions, ResourceOptions, SchedulingOptions, job


@job(
    options=JobOptions(
        resources=ResourceOptions(memory="256Mi", cpu="4"),
        scheduling=SchedulingOptions(
            queue_name="user-queue",
            priority_class="production",
        ),
    ),
    image=ImageOptions(
        spec=Path("example-hello.yaml"),
        name="localhost:5000/hello-world-prod",
        tag="latest",
    ),
)
def prod_training():
    print("Hello, World!")
    time.sleep(60)
