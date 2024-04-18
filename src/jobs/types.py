import os
from pathlib import Path
from typing import TypeAlias

AnyPath: TypeAlias = os.PathLike[str] | str | Path
