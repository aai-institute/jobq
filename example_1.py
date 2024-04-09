import argparse
import enum
import logging

from jobs import ImageBuilder, JobOptions, ResourceOptions, job
from jobs.runner import DockerRunner, KueueRunner, RayClusterRunner


@job(
    options=JobOptions(
        resources=ResourceOptions(memory="256Mi", cpu="1"),
    )
)
def myjob() -> None:
    print("Hello, world")


# TODO: Hack for Ray with Python 3.10
class ExecutionMode(enum.Enum):
    LOCAL = "local"
    DOCKER = "docker"
    KUEUE = "kueue"
    RAYCLUSTER = "raycluster"


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
        # TODO: Figure out 3.10-compatible solution
        # choices=[val for val in ExecutionMode],
        type=ExecutionMode,
    )

    parser.add_argument(
        "--kueue-local-queue",
        help="Name of the Kueue LocalQueue to submit the workload to",
        default="user-queue",
    )

    parser.add_argument(
        "--namespace",
        help="Kubernetes namespace to create resources in, defaults to currently active namespace",
    )

    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

    argparser = _make_parser()
    args, _ = argparser.parse_known_args()

    mode = args.mode
    logging.debug(f"Execution mode: {mode}")

    image = None
    if mode in [ExecutionMode.DOCKER, ExecutionMode.KUEUE]:
        image = ImageBuilder.from_dockerfile(args.image_name)

    if mode == ExecutionMode.DOCKER:
        # Submit the job as a container
        DockerRunner().run(myjob, image)
    elif mode == ExecutionMode.KUEUE:
        # Submit the job as a Kueue Kubernetes Job
        runner = KueueRunner(
            namespace=args.namespace,
            local_queue=args.kueue_local_queue,
        )
        runner.run(myjob, image)
    elif mode == ExecutionMode.RAYCLUSTER:
        # Submit the job to a new Ray cluster
        runner = RayClusterRunner(
            namespace=args.namespace,
            # TODO: Hard-coded
            head_url="http://localhost:8265",
        )
        runner.run(myjob, image)
    elif mode == ExecutionMode.LOCAL:
        # Run the job locally
        myjob()
