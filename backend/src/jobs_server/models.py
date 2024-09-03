import json
import re
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any, Self, TypeAlias

from fastapi import HTTPException, status
from jobs import JobOptions
from pydantic import AfterValidator, BaseModel, Field, StrictStr, field_validator

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
    managed_resource_id: JobId
    execution_status: JobStatus
    spec: WorkloadSpec
    kueue_status: WorkloadStatus

    @classmethod
    def from_managed_workload(cls, workload: "ManagedWorkload") -> Self:
        if workload.owner_uid is None:
            raise ValueError("Workload has no owner UID")
        return WorkloadMetadata(
            managed_resource_id=workload.owner_uid,
            execution_status=workload.execution_status,
            spec=workload.spec,
            kueue_status=workload.status,
        )


class LogsParams(BaseModel):
    stream: bool = Field(default=False, description="Whether to stream the logs")
    tail: int = Field(
        default=100, description="Number of tail lines of logs, -1 for all"
    )

    @field_validator("tail")
    @classmethod
    def validate_tail(cls, v):
        if v < -1:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="tail must be -1 or non-negative integer",
            )
        return v
