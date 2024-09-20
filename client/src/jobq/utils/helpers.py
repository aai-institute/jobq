from __future__ import annotations

import re
import textwrap
from collections.abc import Mapping
from typing import Any, TypeVar, cast

T = TypeVar("T", bound=Mapping[str, Any])


def remove_none_values(d: T) -> T:
    """Remove all keys with a ``None`` value from a dict."""
    filtered_dict = {k: v for k, v in d.items() if v is not None}
    return cast(T, filtered_dict)


def snake_to_human(s: str) -> str:
    """Convert a snake_case string to a human-readable string."""
    return s.replace("_", " ")


def camel_to_human(s: str) -> str:
    """Convert a camelCase string to a human-readable string.

    Examples
    --------
    >>> camel_to_human("camelCase")
    'Camel Case'
    >>> camel_to_human("camelCaseString")
    'Camel Case String'
    >>> camel_to_human("randomID")
    'Random ID'
    """
    # Use regex to find positions where a lowercase letter is followed by an uppercase letter
    s = re.sub("([a-z])([A-Z])", r"\1 \2", s)

    # Capitalize the first letter of each word
    return s


def to_human(s: str) -> str:
    """Convert a string to a human-readable string."""
    result = s
    if s.islower():
        result = snake_to_human(s)
    else:
        result = camel_to_human(s)
    return result.title()


def format_dict(d: Mapping[str, Any], level: int = 0, indent_width: int = 2) -> str:
    """Format a dict in a human-readable format.

    Simple values are printed as-is, lists are printed as comma-separated values,
    and dicts are recursively formatted with keys as section headers.
    """

    def format_value(value: Any, level: int) -> str:
        if isinstance(value, Mapping):
            return format_dict(value, level + 1)
        elif isinstance(value, list):
            return "\n".join(
                " " * ((level + 1) * indent_width)
                + "- "
                + format_value(item, level + 1).strip()
                for item in value
            )
        else:
            strval = str(value).strip()
            if "\n" in strval:
                return "\n" + textwrap.indent(
                    strval, prefix=" " * (level * indent_width)
                )
            else:
                return strval

    indent = " " * (level * indent_width)
    formatted_items = []

    for key, value in d.items():
        formatted_value = format_value(value, level) or f"{indent}    <empty>"
        header = f"{indent}{to_human(key)}"

        if isinstance(value, list | Mapping):
            formatted_items.append(f"{header}:\n{formatted_value}\n")
        else:
            formatted_items.append(f"{header}: {formatted_value}")

    return "\n".join(formatted_items)
