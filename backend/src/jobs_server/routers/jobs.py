from fastapi import APIRouter, HTTPException
from jobs import Image, Job

from jobs_server.models import CreateJobModel, ExecutionMode, WorkloadIdentifier
from jobs_server.runner import Runner

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
