import json
import os
from enum import Enum
from pathlib import Path
from typing import TypeAlias, TypedDict

from typing_extensions import Self

AnyPath: TypeAlias = os.PathLike[str] | str | Path


class K8sResourceKind(Enum):
    REQUESTS = "requests"
    LIMITS = "limits"


class ExecutionMode(str, Enum):
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


class NoOptions(TypedDict, total=True):
    pass
