import time
from pathlib import Path

from jobs import ImageOptions, JobOptions, ResourceOptions, SchedulingOptions, job


@job(
    options=JobOptions(
        # A job with explicit Dockerfile
        image=ImageOptions(dockerfile=Path("Dockerfile")),
        resources=ResourceOptions(memory="256Mi", cpu="4"),
        scheduling=SchedulingOptions(
            priority_class="production",
        ),
    )
)
def prod_training():
    print("Hello, World!")
    time.sleep(60)
