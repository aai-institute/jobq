import pytest

from jobs.util import to_rational


@pytest.mark.parametrize(
    "input, expected",
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
def test_to_rational(input: str, expected: float):
    actual = to_rational(input)

    assert actual == pytest.approx(expected)
