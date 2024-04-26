from __future__ import annotations

import argparse
import logging

from jobs import Image, Job
from jobs.runner import (
    DockerRunner,
    ExecutionMode,
    KueueRunner,
    RayClusterRunner,
    RayJobRunner,
)


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

    def _build_image(job: Job) -> Image:
        push = mode != ExecutionMode.DOCKER  # no need to push image for local execution
        image = job.build_image(push=push)
        if image is None:
            raise RuntimeError("Could not build container image")
        return image

    match mode:
        case ExecutionMode.DOCKER:
            # Submit the job as a container
            DockerRunner().run(job, _build_image(job))
        case ExecutionMode.KUEUE:
            # Submit the job as a Kueue Kubernetes Job
            kueue_runner = KueueRunner(
                namespace=args.namespace,
                local_queue=args.kueue_local_queue,
            )
            kueue_runner.run(job, _build_image(job))
        case ExecutionMode.RAYCLUSTER:
            # Submit the job to a running Ray cluster
            ray_cluster_runner = RayClusterRunner(
                namespace=args.namespace,
                head_url=args.ray_head_url,
            )
            ray_cluster_runner.run(job, _build_image(job))
        case ExecutionMode.RAYJOB:
            # Submit the job as a Kuberay `RayJob`
            ray_job_runner = RayJobRunner(
                namespace=args.namespace,
            )
            ray_job_runner.run(job, _build_image(job))
        case ExecutionMode.LOCAL:
            # Run the job locally
            job()
