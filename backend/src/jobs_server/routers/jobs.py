import itertools
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi import status as http_status
from fastapi.responses import StreamingResponse
from jobs import Image, Job

from jobs_server.dependencies import Kubernetes, ManagedWorkload
from jobs_server.exceptions import PodNotReadyError
from jobs_server.models import (
    CreateJobModel,
    ExecutionMode,
    ListWorkloadModel,
    LogOptions,
    WorkloadIdentifier,
    WorkloadMetadata,
)
from jobs_server.runner import Runner
from jobs_server.utils.fastapi import make_dependable
from jobs_server.utils.kueue import JobId

router = APIRouter(tags=["Job management"])


@router.post("")
async def submit_job(
    opts: CreateJobModel,
    k8s: Kubernetes,
) -> WorkloadIdentifier:
    # FIXME: Having to define a function just to set the job name is ugly
    def job_fn(): ...

    job_fn.__name__ = opts.name
    job = Job(job_fn, options=opts.options)
    job._file = opts.file

    if opts.mode == ExecutionMode.LOCAL:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported job execution mode: {opts.mode!r}",
        )

    runner = Runner.for_mode(opts.mode, k8s=k8s)
    if runner is None:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported job execution mode: {opts.mode!r}",
        )

    image = Image(opts.image_ref)
    workload_id = runner.run(job, image, opts.submission_context)
    return workload_id


@router.get("/{uid}/status")
async def status(
    workload: ManagedWorkload,
) -> WorkloadMetadata:
    try:
        return WorkloadMetadata.from_kueue_workload(workload)
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Workload not found or invalid: {str(e)}",
        ) from e


@router.get("/{uid}/logs")
async def logs(
    workload: ManagedWorkload,
    k8s: Kubernetes,
    params: Annotated[LogOptions, Depends(make_dependable(LogOptions))],
):
    try:
        if params.stream:

            def roundrobin(*iterables):
                """
                Stream logs from n pods as n-tuples synchronoously.

                NB: This means that the stream yields only when the last
                pod log is available, meaning that logs can stall if the
                logging frequencies vary a lot between different pods.
                """
                # Algorithm credited to George Sakkis
                iterators = map(iter, iterables)
                for num_active in range(len(iterables), 0, -1):
                    iterators = itertools.cycle(itertools.islice(iterators, num_active))
                    yield from map(next, iterators)

            streams = []
            for pod in workload.pods:
                streams.append(k8s.stream_pod_logs(pod, tail=params.tail))
            return StreamingResponse(roundrobin(*streams), media_type="text/plain")
        else:
            if len(workload.pods) == 0:
                raise HTTPException(
                    http_status.HTTP_404_NOT_FOUND,
                    "workload pod not found",
                )
            log = ""
            # appends all logs to a single master log, similarly to how
            # kubectl logs job/<id> --all-pods does.
            for pod in workload.pods:
                log += k8s.get_pod_logs(pod, tail=params.tail)
            return log
    except PodNotReadyError as e:
        raise HTTPException(http_status.HTTP_400_BAD_REQUEST, "pod not ready") from e


@router.post("/{uid}/stop")
async def stop_workload(
    uid: JobId,
    workload: ManagedWorkload,
    k8s: Kubernetes,
):
    try:
        workload.stop(k8s)
        return Response(
            status_code=http_status.HTTP_200_OK,
            content=f"Stopped owner workload {workload.owner_uid} of {uid}, including all its children",
        )
    except Exception as e:
        logging.error(f"Failed to stop workload {workload.owner_uid}", exc_info=True)
        raise HTTPException(
            http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Failed to terminate workload",
        ) from e


@router.get("", response_model_exclude_unset=True)
async def list_jobs(
    k8s: Kubernetes,
    include_metadata: Annotated[bool, Query()] = False,
) -> list[ListWorkloadModel]:
    workloads = k8s.list_workloads()
    if include_metadata:
        return [
            ListWorkloadModel(
                name=workload.metadata.name,
                id=WorkloadIdentifier.from_kueue_workload(workload),
                metadata=WorkloadMetadata.from_kueue_workload(workload),
            )
            for workload in workloads
        ]
    else:
        return [
            ListWorkloadModel(
                name=workload.metadata.name,
                id=WorkloadIdentifier.from_kueue_workload(workload),
            )
            for workload in workloads
        ]
