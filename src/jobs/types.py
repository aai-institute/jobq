import os
from enum import Enum
from pathlib import Path
from typing import TypeAlias, TypedDict

AnyPath: TypeAlias = os.PathLike[str] | str | Path


class K8sResourceKind(Enum):
    REQUESTS = "requests"
    LIMITS = "limits"


NoOptions = TypedDict("NoOptions", {}, total=True)
