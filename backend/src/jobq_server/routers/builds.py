import asyncio
import io
import shlex
import tarfile
import tempfile
import uuid
from copy import deepcopy
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from jobq_server.utils.assembler import config
from jobq_server.utils.assembler.renderers import RENDERERS
from jobq_server.utils.processes import run_command

router = APIRouter(tags=["Container image builds"])

# In-memory storage for build jobs
build_jobs: dict[str, dict] = {}


class BuildJob(BaseModel):
    id: str
    status: str
    logs: list[str]


async def build_image(job_id: str, build_context: UploadFile, image_spec: UploadFile):
    build_jobs[job_id]["status"] = "in_progress"

    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract the build context to the temporary directory
        with tarfile.TarFile.open(fileobj=build_context.file, mode="r:gz") as tarf:
            tarf.extractall(tmpdir)

        image_cfg = config.load_config(image_spec.file)
        renderers = [cls(image_cfg) for cls in RENDERERS if cls.accepts(image_cfg)]
        dockerfile_content = ""
        for r in renderers:
            dockerfile_content += r.render() + "\n"

        tag = f"jobq-build-{job_id}"
        build_cmd = [
            "docker",
            "buildx",
            "build",
            "-t",
            tag,
            "-f",
            "-",
            str(tmpdir),
        ]

        with io.StringIO(dockerfile_content) as dockerfile:
            build_jobs[job_id]["logs"] = []
            exit_code, _, _, _ = run_command(
                shlex.join(build_cmd),
                verbose=True,
                stdin=dockerfile,
                stdout_stream=build_jobs[job_id]["logs"],
                stderr_stream=build_jobs[job_id]["logs"],
            )

        if exit_code != 0:
            build_jobs[job_id]["status"] = "failed"
            build_jobs[job_id]["logs"].append("Build failed.")
        else:
            build_jobs[job_id]["status"] = "completed"
            build_jobs[job_id]["logs"].append("Build completed successfully.")


@router.post("/build")
async def create_build(
    background_tasks: BackgroundTasks,
    image_spec: Annotated[UploadFile, File(...)],
    build_context: Annotated[UploadFile, File(...)],
):
    extension = Path(build_context.filename).suffixes
    if extension not in [[".tgz"], [".tar", ".gz"]]:
        raise HTTPException(
            status_code=400, detail=f"File must be a gzipped TAR archive: {extension}"
        )

    job_id = str(uuid.uuid4())
    build_jobs[job_id] = {"status": "queued", "logs": []}

    background_tasks.add_task(
        build_image,
        job_id,
        deepcopy(build_context),
        deepcopy(image_spec),
    )

    return JSONResponse(content={"job_id": job_id, "status": "queued"}, status_code=202)


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
        for log in build_jobs[job_id]["logs"]:
            yield f"{log}\n"

        while build_jobs[job_id]["status"] != "completed":
            await asyncio.sleep(1)
            new_logs = build_jobs[job_id]["logs"][len(build_jobs[job_id]["logs"]) :]
            for log in new_logs:
                yield f"{log}\n"

    return StreamingResponse(log_generator(), media_type="text/plain")
