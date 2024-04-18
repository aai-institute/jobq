import argparse
import logging

from jobs import Image, Job
from jobs.runner import DockerRunner, ExecutionMode, KueueRunner, RayClusterRunner


def _make_argparser() -> argparse.ArgumentParser:
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
        choices=list(ExecutionMode),
        type=ExecutionMode,
    )

    parser.add_argument(
        "--kueue-local-queue",
        help="Name of the Kueue LocalQueue to submit the workload to",
        default="user-queue",
    )

    parser.add_argument(
        "--ray-head-url",
        help="URL of the Ray cluster head node",
        default="http://localhost:8265",
    )

    parser.add_argument(
        "--namespace",
        help="Kubernetes namespace to create resources in, defaults to currently active namespace",
    )

    return parser


def submit_job(job: Job) -> None:
    args = _make_argparser().parse_args()
    mode = args.mode
    logging.debug(f"Execution mode: {mode}")

    image: Image | None = None
    if mode in [ExecutionMode.DOCKER, ExecutionMode.KUEUE]:
        image = job.build_image()
        if image is None:
            raise RuntimeError("Could not build container image")

    if mode == ExecutionMode.DOCKER:
        # Submit the job as a container
        DockerRunner().run(job, image)
    elif mode == ExecutionMode.KUEUE:
        # Submit the job as a Kueue Kubernetes Job
        runner = KueueRunner(
            namespace=args.namespace,
            local_queue=args.kueue_local_queue,
        )
        runner.run(job, image)
    elif mode == ExecutionMode.RAYCLUSTER:
        # Submit the job to a Ray cluster
        runner = RayClusterRunner(
            namespace=args.namespace,
            head_url=args.ray_head_url,
        )
        runner.run(job, image)
    elif mode == ExecutionMode.LOCAL:
        # Run the job locally
        job()
