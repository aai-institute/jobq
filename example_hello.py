import time
from pathlib import Path

from jobs import (
    ImageOptions,
    JobOptions,
    Metadata,
    ResourceOptions,
    SchedulingOptions,
    job,
)


@job(
    options=JobOptions(
        image=ImageOptions(
            spec=Path("example-docker.yaml"),
            name="localhost:5000/hello-world-dev",
            tag="latest",
        ),
        metadata=Metadata(
            annotations={
                "x-jobby.io/notify-channel": "slack",
                "x-jobby.io/slack-channel-ids": "mlops-test",
            }
        ),
        resources=ResourceOptions(memory="1Gi", cpu="1"),
        scheduling=SchedulingOptions(
            priority_class="background", queue_name="user-queue"
        ),
    )
)
def hello_world():
    start_ts = time.perf_counter()
    print("Hello, World!")
    time.sleep(2)
    end_ts = time.perf_counter()
    print(f"Elapsed: {end_ts - start_ts:.2f} s")
