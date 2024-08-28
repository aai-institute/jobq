import json
import re
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any, Self, TypeAlias

from jobs import JobOptions
from pydantic import AfterValidator, BaseModel, Field, StrictStr

from jobs_server.utils.kueue import JobId, WorkloadSpec, WorkloadStatus

if TYPE_CHECKING:
    from jobs_server.dependencies import ManagedWorkload


def validate_image_ref(ref: str) -> str:
    pattern = re.compile(
        r"^"  # Start of the string
        r"("  # Begin optional registry
        r"([a-zA-Z0-9]+([._-][a-zA-Z0-9]+)*)"  # Registry name part
        r"(:[0-9]+)?"  # Optional port
        r"/)?"  # End optional registry
        r"("  # Begin repository part
        r"[a-zA-Z0-9]+([._-][a-zA-Z0-9]+)*"  # Repository name part
        r"(/([a-zA-Z0-9]+([._-][a-zA-Z0-9]+)*))*"  # Optional repository path
        r")"  # End repository part
        r"(:([a-zA-Z0-9]+([._-][a-zA-Z0-9]+)*))?"  # Optional tag
        r"(@sha256:[a-f0-9]{64})?"  # Optional digest
        r"$"  # End of the string
    )
    assert re.match(pattern, ref) is not None, f"not a valid image ref: {ref!r}"
    return ref


ImageRef = Annotated[str, AfterValidator(validate_image_ref)]

SubmissionContext: TypeAlias = dict[str, Any]


class ExecutionMode(StrEnum):
    """
    ExecutionMode
    """

    """
    allowed enum values
    """
    LOCAL = "local"
    DOCKER = "docker"
    KUEUE = "kueue"
    RAYCLUSTER = "raycluster"
    RAYJOB = "rayjob"

    @classmethod
    def from_json(cls, json_str: str) -> Self:
        """Create an instance of ExecutionMode from a JSON string"""
        return cls(json.loads(json_str))


class CreateJobModel(BaseModel):
    name: str
    file: str
    image_ref: ImageRef
    mode: ExecutionMode
    options: JobOptions
    submission_context: SubmissionContext = Field(default_factory=dict)


class WorkloadIdentifier(BaseModel):
    """Identifier for a workload in a Kubernetes cluster"""

    group: StrictStr
    version: StrictStr
    kind: StrictStr

    namespace: StrictStr
    uid: StrictStr


class JobStatus(StrEnum):
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        return self in [self.FAILED, self.SUCCEEDED]


class WorkloadMetadata(BaseModel):
    workload_uid: JobId
    execution_status: JobStatus
    spec: WorkloadSpec
    status: WorkloadStatus

    @classmethod
    def from_managed_workload(cls, workload: "ManagedWorkload") -> "WorkloadMetadata":
        if workload.owner_uid is None:
            raise ValueError("Workload has no owner UID")
        return cls(
            workload_uid=workload.owner_uid,
            execution_status=workload.execution_status,
            spec=workload.spec,
            status=workload.status,
        )
