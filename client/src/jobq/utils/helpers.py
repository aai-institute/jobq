from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, cast

T = TypeVar("T", bound=Mapping[str, Any])


def remove_none_values(d: T) -> T:
    """Remove all keys with a ``None`` value from a dict."""
    filtered_dict = {k: v for k, v in d.items() if v is not None}
    return cast(T, filtered_dict)
