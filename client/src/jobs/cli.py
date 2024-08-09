from __future__ import annotations

import argparse
import logging
import os
import sys

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

    parser.add_argument("entrypoint")

    return parser


def submit_job(job: Job, args: argparse.Namespace) -> None:
    def _build_image(job: Job) -> Image:
        push = mode != ExecutionMode.DOCKER  # no need to push image for local execution
        image = job.build_image(push=push)
        if image is None:
            raise RuntimeError("Could not build container image")
        return image

    mode = args.mode
    logging.debug(f"Execution mode: {mode}")
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


def discover_job(args: argparse.Namespace) -> Job:
    import importlib.util
    import inspect

    module_file = args.entrypoint
    module_dir = os.path.dirname(module_file)
    module_name = module_file.replace("/", ".").removesuffix(".py")

    if module_name in sys.modules:
        logging.debug(f"Module {module_name!r} already loaded")
    else:
        logging.debug(f"Loading module {module_name!r} from {module_file!r}")
        spec = importlib.util.spec_from_file_location(
            module_name,
            module_file,
        )
        if not spec or not spec.loader:
            logging.error(f"Could not load module {module_name!r} from {module_file!r}")
            sys.exit(1)

        module = importlib.util.module_from_spec(spec)

        # Support relative imports from the workload module
        if module_dir not in sys.path:
            logging.debug(f"Adding {module_dir!r} to the Python search path")
            sys.path.append(module_dir)

        sys.modules[module_name] = module
        spec.loader.exec_module(module)

    all_jobs = dict(inspect.getmembers(module, lambda m: isinstance(m, Job)))
    logging.debug(f"Discovered jobs: {all_jobs}")

    return next(iter(all_jobs.values()))


def main():
    """CLI entrypoint for job submission"""

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

    args = _make_argparser().parse_args()
    job = discover_job(args)

    submit_job(job, args)
