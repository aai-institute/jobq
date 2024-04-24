import abc
import enum

from jobs import Image, Job


class Runner(abc.ABC):
    @abc.abstractmethod
    def run(self, job: Job, image: Image) -> None: ...


class ExecutionMode(enum.Enum):
    LOCAL = "local"
    DOCKER = "docker"
    KUEUE = "kueue"
    RAYCLUSTER = "raycluster"


def _make_executor_command(job: Job) -> list[str]:
    """Build the command line arguments for running a job locally through the job executor."""
    return [
        "jobs_execute",
        job.file,
        job.name,
    ]
