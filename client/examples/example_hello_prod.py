import time
from pathlib import Path

from jobs import ImageOptions, JobOptions, ResourceOptions, SchedulingOptions, job


@job(
    options=JobOptions(
        resources=ResourceOptions(memory="256Mi", cpu="4"),
        scheduling=SchedulingOptions(
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
