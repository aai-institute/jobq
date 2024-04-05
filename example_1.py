import argparse
import enum
import logging

from jobs import ImageBuilder, job
from jobs.runner import DockerRunner, KueueRunner


@job
def myjob() -> None:
    print("Hello, world")


class ExecutionMode(enum.StrEnum):
    LOCAL = enum.auto()
    DOCKER = enum.auto()
    KUEUE = enum.auto()


def _make_parser():
    parser = argparse.ArgumentParser(
        description="Run an example job either locally, or on a container execution platform",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--image-name",
        help="Image name to use when building a container image",
        default="example:latest",
    )

    parser.add_argument(
        "--mode",
        help="Job execution mode",
        default="local",
        choices=[val for val in ExecutionMode],
        type=ExecutionMode,
    )

    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

    argparser = _make_parser()
    args, _ = argparser.parse_known_args()

    mode = args.mode
    logging.debug(f"Execution mode: {mode}")

    if mode != ExecutionMode.LOCAL:
        image = ImageBuilder.from_dockerfile(args.image_name)

    if mode == ExecutionMode.DOCKER:
        # Submit the job as a container
        DockerRunner.run(myjob, image)
    elif mode == ExecutionMode.KUEUE:
        # Submit the job as a Kueue Kubernetes Job
        KueueRunner.run(myjob, image)
    elif mode == ExecutionMode.LOCAL:
        # Run the job locally
        myjob()
