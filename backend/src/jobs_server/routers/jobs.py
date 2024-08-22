from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from jobs import Image, Job

from jobs_server.dependencies import k8s_service
from jobs_server.exceptions import PodNotReadyError
from jobs_server.models import CreateJobModel, ExecutionMode, JobId, WorkloadIdentifier
from jobs_server.runner import Runner
from jobs_server.services.k8s import KubernetesService

router = APIRouter(tags=["Job management"])


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
            status_code=400, detail=f"unsupported job execution mode: {opts.mode!r}"
        )

    runner = Runner.for_mode(opts.mode)
    if runner is None:
        raise HTTPException(
            status_code=400, detail=f"unsupported job execution mode: {opts.mode!r}"
        )

    image = Image(opts.image_ref)
    workload_id = runner.run(job, image, opts.submission_context)
    return workload_id


@router.get("/jobs/{uid}/status")
async def status(
    k8s: Annotated[KubernetesService, Depends(k8s_service)],
    uid: JobId,
    namespace: str = "default",
):
    workload = k8s.workload_for_managed_resource(uid, namespace)
    if workload is None:
        raise HTTPException(404, "workload not found")
    return workload.execution_status


@router.get("/jobs/{uid}/logs")
async def logs(
    k8s: Annotated[KubernetesService, Depends(k8s_service)],
    uid: JobId,
    namespace: str = "default",
    stream: bool = False,
    tail: int = 100,
):
    workload = k8s.workload_for_managed_resource(uid, namespace)
    if workload is None:
        raise HTTPException(404, "workload not found")

    try:
        if stream:
            log_stream = k8s.stream_pod_logs(workload.pod, tail=tail)
            return StreamingResponse(log_stream, media_type="text/plain")
        else:
            return k8s.get_pod_logs(workload.pod, tail=tail)
    except PodNotReadyError as e:
        raise HTTPException(400, "pod not ready") from e


@router.get("/jobs/{uid}/kill")
async def terminate(
    k8s: Annotated[KubernetesService, Depends(k8s_service)],
    uid: JobId,
    namespace: str = "default",
):
    workload = k8s.workload_for_managed_resource(uid, namespace)
    if workload is None:
        raise HTTPException(404, "workload not found")
    try:
        success = k8s.terminate_workload(workload)
        if success:
            return {"message": f"Job {uid} terminated"}
        else:
            raise HTTPException(500, f"Failed to terminate job, {uid}")
    except Exception as e:
        raise HTTPException(500, f"Error terminating job, {uid}: {str(e)}") from e
