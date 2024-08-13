from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from jobs import Image, Job
from kubernetes import client

from jobs_server.models import CreateJobModel, ExecutionMode
from jobs_server.runner import Runner

router = APIRouter(tags=["Job management"])


@router.post("/jobs")
async def submit_job(opts: CreateJobModel):
    image = Image(opts.image_ref)

    # FIXME: Having to define a function just to set the job name is ugly
    def job_fn(): ...

    job_fn.__name__ = opts.name
    job = Job(job_fn, options=opts.options)
    job._file = opts.file

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


def stream_pod_logs(pod: client.V1Pod):
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


@router.get(
    "/jobs/{job_id}/logs",
)
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

    return StreamingResponse(stream_pod_logs(pods[0]), media_type="text/plain")
