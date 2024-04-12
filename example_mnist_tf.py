import logging

from jobs import JobOptions, ResourceOptions, job
from jobs.cli import submit_job

USE_GPU = True


@job(
    options=JobOptions(
        resources=ResourceOptions(memory="4Gi", cpu="2", gpu=1 if USE_GPU else None),
    )
)
def mnist_train() -> None:
    from mnist_tf import train_tensorflow_mnist
    train_tensorflow_mnist(1, use_gpu=USE_GPU, epochs=16)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

    submit_job(mnist_train)
