import asyncio
import io
import shlex
import tarfile
import tempfile
import uuid
from copy import deepcopy
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from jobq_server.utils.assembler import config
from jobq_server.utils.assembler.renderers import RENDERERS
from jobq_server.utils.processes import run_command

router = APIRouter(tags=["Container image builds"])

# In-memory storage for build jobs
build_jobs: dict[str, dict] = {}


class BuildJobStatus(str, Enum):  # noqa: UP042
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class BuildJob(BaseModel):
    id: str
    status: BuildJobStatus
    logs: list[str]


@dataclass
class BuildOptions:
    name: str = Form()
    tag: str = Form(default="latest")
    platform: str = Form(default="linux/amd64")


def build_image(
    job_id: str,
    options: BuildOptions,
    build_context: UploadFile,
    image_spec: UploadFile,
):
    build_jobs[job_id]["status"] = BuildJobStatus.IN_PROGRESS

    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract the build context to the temporary directory
        with tarfile.TarFile.open(fileobj=build_context.file, mode="r:gz") as tarf:
            tarf.extractall(tmpdir)

        image_cfg = config.load_config(image_spec.file)
        renderers = [cls(image_cfg) for cls in RENDERERS if cls.accepts(image_cfg)]
        dockerfile_content = ""
        for r in renderers:
            dockerfile_content += r.render() + "\n"

        with io.StringIO(dockerfile_content) as dockerfile:
            build_jobs[job_id]["logs"] = []

            build_cmd = [
                "docker",
                "buildx",
                "build",
                "--platform",
                options.platform,
                "-t",
                f"{options.name}:{options.tag}",
                "-f",
                "-",
                str(tmpdir),
            ]

            exit_code, _, _, _ = run_command(
                shlex.join(build_cmd),
                verbose=True,
                stdin=dockerfile,
                stdout_stream=build_jobs[job_id]["logs"],
                stderr_stream=build_jobs[job_id]["logs"],
            )

        if exit_code != 0:
            build_jobs[job_id]["status"] = BuildJobStatus.FAILED
            build_jobs[job_id]["logs"].append("Build failed.")
        else:
            build_jobs[job_id]["status"] = BuildJobStatus.COMPLETED
            build_jobs[job_id]["logs"].append("Build completed successfully.")


@router.post("/build")
async def create_build(
    background_tasks: BackgroundTasks,
    options: Annotated[BuildOptions, Depends()],
    image_spec: UploadFile,
    build_context: UploadFile,
):
    extension = Path(build_context.filename).suffixes
    if extension not in [[".tgz"], [".tar", ".gz"]]:
        raise HTTPException(
            status_code=400, detail=f"File must be a gzipped TAR archive: {extension}"
        )

    job_id = str(uuid.uuid4())
    build_jobs[job_id] = {"status": "queued", "logs": []}

    # Need to deepcopy the uploaded files to avoid issues with the background task not being able to access them
    # See https://github.com/fastapi/fastapi/discussions/10936
    # and https://github.com/fastapi/fastapi/issues/10857
    background_tasks.add_task(
        build_image,
        job_id,
        options,
        deepcopy(build_context),
        deepcopy(image_spec),
    )

    return JSONResponse(
        content={"job_id": job_id, "status": BuildJobStatus.QUEUED}, status_code=202
    )


@router.get("/build/{job_id}", response_model=BuildJob)
async def get_build_status(job_id: str):
    if job_id not in build_jobs:
        raise HTTPException(status_code=404, detail="Build job not found")

    return BuildJob(id=job_id, **build_jobs[job_id])


@router.get("/build/{job_id}/logs")
async def stream_build_logs(job_id: str):
    if job_id not in build_jobs:
        raise HTTPException(status_code=404, detail="Build job not found")

    async def log_generator():
        # Asynchronously iterate over the log list, while the builder subprocess appends to it.
        # Cannot use an iterator due to the concurrent modification of the list.
        last_index = 0
        while build_jobs[job_id]["status"] != BuildJobStatus.COMPLETED:
            for line in build_jobs[job_id]["logs"][last_index:]:
                yield line
            last_index = len(build_jobs[job_id]["logs"])
            await asyncio.sleep(0.1)

    return StreamingResponse(log_generator(), media_type="text/plain")
