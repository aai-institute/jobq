import re


def to_rational(s: str) -> float:
    """Convert a number with optional SI/binary unit to floating-point"""

    matches = re.match(r"(?P<magnitude>[+\-]?\d*[.,]?\d+)(?P<suffix>[a-zA-Z]*)", s)
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


def remove_none_values(d: dict) -> dict:
    """Remove all keys with a ``None`` value from a dict."""
    return {k: v for k, v in d.items() if v is not None}


def sanitize_rfc1123_domain_name(s: str) -> str:
    """Sanitize a string to be compliant with RFC 1123 domain name

    Note: Any invalid characters are replaced with dashes."""

    # TODO: This is obviously wildly incomplete
    return s.replace("_", "-")
