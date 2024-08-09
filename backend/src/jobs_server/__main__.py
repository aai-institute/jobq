from contextlib import asynccontextmanager

import jobs
import jobs.runner
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from jobs import Image, Job
from jobs.runner.base import ExecutionMode
from kubernetes import client, config

from jobs_server.models import CreateJobModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.load_config()
    yield


app = FastAPI(lifespan=lifespan)


@app.post("/jobs")
async def submit_job(opts: CreateJobModel):
    image = Image(opts.image_ref)

    def job_fn(): ...

    job_fn.__name__ = opts.name
    job = Job(job_fn, options=opts.metadata)
    if opts.mode == ExecutionMode.RAYJOB:
        job_uid = jobs.runner.RayJobRunner().run(job, image)
    elif opts.mode == ExecutionMode.KUEUE:
        job_uid = jobs.runner.KueueRunner().run(job, image)
    else:
        raise HTTPException(
            status_code=400, detail=f"unsupported job execution mode: {opts.mode!r}"
        )

    return job_uid


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
    for line in logs:
        yield line


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
