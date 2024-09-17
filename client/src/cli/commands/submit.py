import argparse
import logging
import sys
from pathlib import Path
from pprint import pp
from typing import Any

import openapi_client
from jobs import Image, Job
from jobs.submission_context import SubmissionContext
from openapi_client import ExecutionMode

from .util import with_job_mgmt_api


def submit(args: argparse.Namespace) -> None:
    job = discover_job(args)

    submit_job(job, args)


def _build_image(job: Job, mode: ExecutionMode) -> Image:
    push = mode != ExecutionMode.DOCKER  # no need to push image for local execution
    image = job.build_image(push=push)
    if image is None:
        raise RuntimeError("Could not build container image")
    return image


@with_job_mgmt_api
def _submit_remote_job(
    client: openapi_client.JobManagementApi, job: Job, mode: ExecutionMode
) -> None:
    # Job options sent to server do not need image options
    if job.options is None:
        raise ValueError(
            f"Missing job options for job {job.name}. Did you add add them in the @job decorator of the entry point?"
        )
    opts = openapi_client.CreateJobModel(
        name=job.name,
        file=job.file,
        image_ref=_build_image(job, mode).tag,
        mode=mode,
        options=openapi_client.JobOptions.model_validate(job.options.model_dump()),
        submission_context=SubmissionContext().to_dict(),
    )
    resp = client.submit_job_jobs_post(opts)
    pp(resp)


def submit_job(job: Job, args: argparse.Namespace) -> None:
    mode = args.mode
    logging.debug(f"Execution mode: {mode}")
    match mode:
        case ExecutionMode.LOCAL:
            # Run the job locally
            job()
        case _:
            _submit_remote_job(job, mode)


def discover_job(args: argparse.Namespace) -> Job:
    import importlib.util
    import inspect

    module_file = args.entrypoint
    module_dir = str(Path(module_file).parent)
    module_name = module_file.replace("/", ".").removesuffix(".py")

    if module_name in sys.modules:
        logging.debug(f"Module {module_name!r} already loaded")
        module = sys.modules[module_name]
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


def add_parser(subparsers: Any, parent: argparse.ArgumentParser) -> None:
    # jobby submit, the job submission command
    parser = subparsers.add_parser(
        "submit",
        parents=[parent],
        description="Run an example job either locally, or on a container execution platform",
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

    parser.add_argument("entrypoint")
    # TODO: Factor out into command class
    parser.set_defaults(func=submit)
