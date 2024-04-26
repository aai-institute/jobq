from pathlib import Path

from jobs import ImageOptions, JobOptions, ResourceOptions, job

USE_GPU = False


@job(
    options=JobOptions(
        image=ImageOptions(spec=Path("example-docker.yaml"), name="mlops:5000/tf-example"),
        resources=ResourceOptions(memory="4Gi", cpu="2", gpu=1 if USE_GPU else None),
    )
)
def mnist_train() -> None:
    from mnist_tf import train_tensorflow_mnist

    train_tensorflow_mnist(1, use_gpu=USE_GPU, epochs=16)
