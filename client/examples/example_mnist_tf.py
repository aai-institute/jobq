from pathlib import Path

from jobq import ImageOptions, JobOptions, ResourceOptions, SchedulingOptions, job

USE_GPU = False


@job(
    image=ImageOptions(
        spec=Path("example-mnist.yaml"), name="localhost:5000/tf-example"
    ),
    options=JobOptions(
        scheduling=SchedulingOptions(queue_name="user-queue"),
        resources=ResourceOptions(memory="2Gi", cpu="2", gpu=1 if USE_GPU else None),
    ),
)
def mnist_train() -> None:
    from mnist_tf import train_tensorflow_mnist

    train_tensorflow_mnist(1, use_gpu=USE_GPU, epochs=16)
