import datetime
import json
import re
from enum import StrEnum
from typing import Annotated, Any, Self, TypeAlias

from annotated_types import Ge
from jobq import JobOptions
from pydantic import AfterValidator, BaseModel, Field, StrictStr

from jobq_server.utils.kueue import JobId, KueueWorkload, WorkloadSpec, WorkloadStatus


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

    @classmethod
    def from_kueue_workload(cls, workload: KueueWorkload) -> Self:
        if len(workload.metadata.owner_references) != 1:
            raise ValueError(
                f"Workload {workload.metadata.uid} has multiple owner references: {workload.metadata.owner_references}"
            )
        owner_ref = workload.metadata.owner_references[0]
        return cls(
            group=owner_ref.api_version.split("/")[0],
            version=owner_ref.api_version.split("/")[1],
            kind=owner_ref.kind,
            uid=owner_ref.uid,
            namespace=workload.metadata.namespace,
        )


class JobStatus(StrEnum):
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INADMISSIBLE = "inadmissible"

    @property
    def is_terminal(self) -> bool:
        return self in [self.FAILED, self.SUCCEEDED]


class WorkloadMetadata(BaseModel):
    managed_resource_id: JobId
    execution_status: JobStatus
    spec: WorkloadSpec
    kueue_status: WorkloadStatus
    submission_timestamp: datetime.datetime
    last_admission_timestamp: datetime.datetime | None = None
    termination_timestamp: datetime.datetime | None = None
    was_evicted: bool = False
    was_inadmissible: bool = False
    has_failed_pods: bool = False

    @classmethod
    def from_kueue_workload(cls, workload: KueueWorkload) -> Self:
        if workload.owner_uid is None:
            raise ValueError("Workload has no owner UID")
        return WorkloadMetadata(
            managed_resource_id=workload.owner_uid,
            execution_status=workload.execution_status,
            spec=workload.spec,
            kueue_status=workload.status,
            submission_timestamp=workload.submission_timestamp,
            last_admission_timestamp=workload.last_admission_timestamp,
            termination_timestamp=workload.termination_timestamp,
            was_evicted=workload.was_evicted,
            was_inadmissible=workload.was_inadmissible,
            has_failed_pods=workload.has_failed_pods,
        )


class LogOptions(BaseModel):
    stream: bool = Field(default=False, description="Whether to stream the logs")
    tail: Annotated[int, Ge(-1)] = Field(
        default=-1,
        description="Number of tail lines of logs, -1 for all",
    )


class ListWorkloadModel(BaseModel):
    name: str
    id: WorkloadIdentifier
    metadata: WorkloadMetadata | None = None
