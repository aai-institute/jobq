import re
from typing import Annotated, Any

from jobs import JobOptions
from pydantic import UUID4, AfterValidator, BaseModel, Field

from jobs_server.runner.base import ExecutionMode


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


class CreateJobModel(BaseModel):
    name: str
    file: str
    image_ref: ImageRef
    mode: ExecutionMode
    options: JobOptions
    submission_context: dict[str, Any] = Field(default_factory=dict)
