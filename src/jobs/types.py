import os
from enum import Enum
from typing import Union

AnyPath = Union[os.PathLike[str], str]


class K8sResourceKind(Enum):
    REQUESTS = "requests"
    LIMITS = "limits"
