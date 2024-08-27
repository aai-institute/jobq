from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from fastapi.responses import StreamingResponse
from jobs import Image, Job

from jobs_server.dependencies import k8s_service, managed_workload
from jobs_server.exceptions import PodNotReadyError
from jobs_server.models import CreateJobModel, ExecutionMode, WorkloadIdentifier
from jobs_server.runner import Runner
from jobs_server.services.k8s import KubernetesService
from jobs_server.utils.kueue import KueueWorkload

router = APIRouter(tags=["Job management"])

ManagedWorkload = Annotated[KueueWorkload, Depends(managed_workload)]
Kubernetes = Annotated[KubernetesService, Depends(k8s_service)]


@router.post("/jobs")
async def submit_job(opts: CreateJobModel) -> WorkloadIdentifier:
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
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported job execution mode: {opts.mode!r}",
        )

    runner = Runner.for_mode(opts.mode)
    if runner is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported job execution mode: {opts.mode!r}",
        )

    image = Image(opts.image_ref)
    workload_id = runner.run(job, image, opts.submission_context)
    return workload_id


@router.get("/jobs/{uid}/status")
async def status(
    workload: ManagedWorkload,
):
    return workload.execution_status


@router.get("/jobs/{uid}/logs")
async def logs(
    workload: ManagedWorkload,
    k8s: Kubernetes,
    stream: bool = False,
    tail: int = 100,
):
    try:
        if stream:
            log_stream = k8s.stream_pod_logs(workload.pod, tail=tail)
            return StreamingResponse(log_stream, media_type="text/plain")
        else:
            return k8s.get_pod_logs(workload.pod, tail=tail)
    except PodNotReadyError as e:
        raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "pod not ready") from e


@router.post("/jobs/{uid}/stop", status_code=http_status.HTTP_204_NO_CONTENT)
async def stop_workload(
    workload: ManagedWorkload,
    k8s: Kubernetes,
):
    try:
        workload.stop(k8s)
    except Exception as e:
        raise HTTPException(
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Failed to terminate workload",
        ) from e
