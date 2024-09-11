from typing import Any

import pytest

from jobs_server.utils.helpers import traverse


@pytest.mark.parametrize(
    "d, key_path, sep, strict, expected",
    [
        # Non-strict mode
        ({"foo": {"bar": {"baz": 42}}}, "foo.bar.baz", ".", False, 42),
        ({"foo": {"bar": {"baz": 42}}}, "foo.bar.qux", ".", False, None),
        ({"foo": {"bar": {"baz": 42}}}, "foo.qux.baz", ".", False, None),
        ({"foo": {"bar": {"baz": None}}}, "foo.bar.baz", ".", False, None),
        # Strict mode
        ({"foo": {"bar": {"baz": 42}}}, "foo.bar.baz", ".", True, 42),
        ({"foo": {"bar": {"baz": 42}}}, "foo.qux.baz", ".", True, KeyError),
        ({"foo": {"bar": {"baz": 42}}}, "foo-bar-qux", "-", True, KeyError),
        ({"foo": {"bar": {"baz": None}}}, "foo.bar.baz", ".", True, None),
    ],
)
def test_path_dict(
    d: dict[str, Any], key_path: str, sep: str, strict: bool, expected: Any
):
    if strict and isinstance(expected, type):
        with pytest.raises(expected):
            traverse(d, key_path, sep, strict)
    else:
        assert traverse(d, key_path, sep, strict) == expected
