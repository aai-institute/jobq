import abc
from typing import ClassVar, Self

from jobq import Job

from jobq_server.models import (
    ExecutionMode,
    ImagePullPolicy,
    ImageRef,
    SubmissionContext,
    WorkloadIdentifier,
)


class Runner(abc.ABC):
    _impls: ClassVar[dict[ExecutionMode, type[Self]]] = {}

    @abc.abstractmethod
    def run(
        self,
        job: Job,
        image: ImageRef,
        context: SubmissionContext,
        pull_policy: ImagePullPolicy = ImagePullPolicy.ALWAYS,
    ) -> WorkloadIdentifier | None: ...

    @classmethod
    def for_mode(cls, mode: ExecutionMode, **kwargs) -> Self | None:
        constructor = cls._impls.get(mode)
        if constructor:
            return constructor(**kwargs)
        else:
            return None

    @classmethod
    def register_implementation(cls, runner: type[Self], mode: ExecutionMode):
        cls._impls[mode] = runner


def _make_executor_command(job: Job) -> list[str]:
    """Build the command line arguments for running a job locally through the job executor."""
    return [
        "jobs_execute",
        job.file,
        job.name,
    ]
