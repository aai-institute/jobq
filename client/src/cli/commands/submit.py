import argparse
import logging
import os
import sys
import tempfile
import zipfile
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


def _pack_job_directory(job_dir: str) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as temp_file:
        with zipfile.ZipFile(temp_file, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(job_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    archive_path = os.path.relpath(file_path, job_dir)
                    zipf.write(file_path, archive_path)
    return temp_file.name


def _generate_image_ref(job: Job) -> str:
    if job.image:
        name = job.image.name or job.name
        tag = job.image.tag or "latest"
    else:
        name = job.name
        tag = "latest"
    return f"{name}:{tag}"


@with_job_mgmt_api
def _submit_remote_job(
    client: openapi_client.JobManagementApi,
    job: Job,
    mode: ExecutionMode,
    server_build: bool,
) -> None:
    # Job options sent to server do not need image options
    if job.options is None:
        raise ValueError(
            f"Missing job options for job {job.name}. Did you add add them in the @job decorator of the entry point?"
        )
    opts = openapi_client.CreateJobModel(
        name=job.name,
        file=job.file,
        image_ref=_generate_image_ref(job),
        mode=mode,
        options=openapi_client.JobOptions.model_validate(job.options.model_dump()),
        submission_context=SubmissionContext().to_dict(),
    )
    if server_build:
        job_dir = os.path.dirname(job.file)
        archive_path = _pack_job_directory(job_dir)

        try:
            with open(archive_path, "rb") as archive_file:
                build_archive = archive_file.read()
        finally:
            os.unlink(archive_path)

        try:
            resp = client.submit_job_jobs_post(opts, build_archive=build_archive)
            pp(resp)
        except Exception:
            print("An unexpected error occured")
            raise
    else:
        if image_ref := _build_image(job, mode).tag is None:
            raise RuntimeError("Failed building image locally")

        opts.image_ref = image_ref
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
            _submit_remote_job(job, mode, args.server_build)


def discover_job(args: argparse.Namespace) -> Job:
    import importlib.util
    import inspect

    module_file = args.entrypoint
    module_dir = os.path.dirname(module_file)
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

    parser.add_argument(
        "--server-build", action="store_true", help="Build image on server"
    )

    parser.add_argument("entrypoint")
    # TODO: Factor out into command class
    parser.set_defaults(func=submit)
