import pytest

from jobq.utils.helpers import remove_none_values
from jobq.utils.math import to_rational


@pytest.mark.parametrize(
    "given, expected",
    [
        ("1", 1),
        # Binary
        ("1Ki", 2**10),
        ("0.1Mi", 0.1 * 2**20),
        ("2.5Gi", 2.5 * 2**30),
        ("-1.0Ti", -1.0 * 2**40),
        # Metric / SI
        ("100m", 0.1),
        ("2k", 2 * 10**3),
        ("1M", 1 * 10**6),
        ("-0.1G", -0.1 * 10**9),
        ("5T", 5 * 10**12),
    ],
)
def test_to_rational(given: str, expected: float) -> None:
    actual = to_rational(given)

    assert actual == pytest.approx(expected)


@pytest.mark.parametrize(
    "given, expected",
    [
        (d := {"a": 1, "b": 2}, d),
        ({"a": 42, "b": None, "c": "foo"}, {"a": 42, "c": "foo"}),
        ({}, {}),
        ({"a": None}, {}),
    ],
)
def test_remove_none_values(given: dict, expected: dict) -> None:
    actual = remove_none_values(given)
    assert actual == expected
