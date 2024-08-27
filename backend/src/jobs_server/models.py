import json
import re
from enum import StrEnum
from typing import Annotated, Any, Self, TypeAlias

from jobs import JobOptions
from pydantic import UUID4, AfterValidator, BaseModel, Field, StrictStr


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
JobId = UUID4

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


class WorkloadExecutionStatus(StrEnum):
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
