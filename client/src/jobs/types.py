import os
from enum import Enum
from pathlib import Path
from typing import Any, TypeAlias, TypedDict

from pydantic import BaseModel
from typing_extensions import Self

AnyPath: TypeAlias = os.PathLike[str] | str | Path


class K8sResourceKind(Enum):
    REQUESTS = "requests"
    LIMITS = "limits"


class NoOptions(TypedDict, total=True):
    pass


class JsonSerializable(BaseModel):
    """Mixin to mark a Pydantic model that can be (de-)serialized to JSON"""

    def to_json(self) -> str:
        return self.model_dump_json(by_alias=True, exclude_unset=True)

    @classmethod
    def from_json(cls, json_data: str) -> Self:
        return cls.model_validate_json(json_data)


class DictSerializable(BaseModel):
    """Mixin to mark a Pydantic model that can be (de-)serialized to a Python dict"""

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)

    @classmethod
    def from_dict(cls, obj: Any) -> Self:
        return cls.model_validate(obj)
