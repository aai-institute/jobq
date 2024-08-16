from __future__ import annotations

import re


def to_rational(s: str) -> float:
    """Convert a number with optional SI/binary unit to floating-point"""

    matches = re.match(r"(?P<magnitude>[+\-]?\d*[.,]?\d+)(?P<suffix>[a-zA-Z]*)", s)
    if not matches:
        raise ValueError(f"Could not parse {s}")
    magnitude = float(matches.group("magnitude"))
    suffix = matches.group("suffix")

    factor = {
        # SI / Metric
        "m": 1e-3,
        "k": 1e3,
        "M": 1e6,
        "G": 1e9,
        "T": 1e12,
        # Binary
        "Ki": 2**10,
        "Mi": 2**20,
        "Gi": 2**30,
        "Ti": 2**40,
        # default
        "": 1.0,
    }.get(suffix)
    if factor is None:
        raise ValueError(f"unknown unit suffix: {suffix}")

    return factor * magnitude
