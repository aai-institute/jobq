import logging
from contextlib import asynccontextmanager
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from jobs_server.models import CreateJobModel
from jobs_server.runner import Runner
from jobs_server.runner.base import ExecutionMode
from kubernetes import client, config
from pydantic import BaseModel

from jobs import Image, Job


class JobStatus(Enum):
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class JobStatusResponse(BaseModel):
    status: JobStatus
    submission_time: datetime | None
    start_time: datetime | None
    completion_time: datetime | None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.DEBUG)
    config.load_config()
    yield


app = FastAPI(
    title="infrastructure-product API",
    description="Backend service for the appliedAI infrastructure product",
    lifespan=lifespan,
)


@app.post("/jobs")
async def submit_job(opts: CreateJobModel):
    image = Image(opts.image_ref)

    # FIXME: Having to define a function just to set the job name is ugly
    def job_fn(): ...

    job_fn.__name__ = opts.name
    job = Job(job_fn, options=opts.options)

    if opts.mode in [
        ExecutionMode.LOCAL,
        ExecutionMode.RAYCLUSTER,
    ]:
        raise HTTPException(
            status_code=400, detail=f"unsupported job execution mode: {opts.mode!r}"
        )

    runner = Runner.for_mode(opts.mode)
    if runner is None:
        raise HTTPException(
            status_code=400, detail=f"unsupported job execution mode: {opts.mode!r}"
        )

    job_uid = runner.run(job, image)
    return job_uid


@app.get("/jobs/{job_status}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str, namespace: str = "default"):
    try:
        api = client.BatchV1Api()
        job = api.read_namespaced_job(name=job_id, namespace=namespace)

        if job.status.active:
            status = JobStatus.EXECUTING
        elif job.status.succeeded:
            status = JobStatus.SUCCEEDED
        elif job.status.failed:
            status = JobStatus.FAILED
        else:
            status = JobStatus.PENDING

        submission_time = job.metadata.creation_timestamp
        start_time = job.status.start_time
        completion_time = job.status.completion_time

        return JobStatusResponse(
            status=status,
            submission_time=submission_time,
            start_time=start_time,
            completion_time=completion_time,
        )
    except client.ApiException as e:
        if e.status == 404:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        else:
            raise HTTPException(status_code=500, details=f"Kubernetes Error: {e}")


def generate_logs(pod: client.V1Pod):
    logs = (
        client.CoreV1Api()
        .read_namespaced_pod_log(
            namespace=pod.metadata.namespace,
            name=pod.metadata.name,
            follow=True,
            _preload_content=False,
        )
        .stream()
    )
    yield from logs


@app.get("/logs/{job_id}")
async def logs(job_id: str, namespace: str = "default"):
    pods = (
        client.CoreV1Api()
        .list_namespaced_pod(
            namespace=namespace,
            label_selector=f"batch.kubernetes.io/job-name={job_id}",
        )
        .items
    )

    if len(pods) == 0:
        raise HTTPException(404, f"no pods found associated with job: {job_id}")

    return StreamingResponse(generate_logs(pods[0]), media_type="text/plain")
