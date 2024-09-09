from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Any, TypeVar, cast

from fastapi import UploadFile

T = TypeVar("T", bound=Mapping[str, Any])


def remove_none_values(d: T) -> T:
    """Remove all keys with a ``None`` value from a dict."""
    filtered_dict = {k: v for k, v in d.items() if v is not None}
    return cast(T, filtered_dict)


async def extract_archive(archive: UploadFile, destination: str) -> None:
    archive_path = os.path.join(destination, archive.filename)

    try:
        with open(archive_path, "wb") as buffer:
            buffer.write(await archive.read())

            if archive.filename.endswith(".zip"):
                import zipfile

                with zipfile.ZipFile(archive_path, "r") as zip_ref:
                    zip_ref.extractall(destination)

            elif archive.filename.endswith((".tar.gz", ".tgz")):
                import tarfile

                with tarfile.open(archive_path, "r:gz") as tar_ref:
                    tar_ref.extractall(destination)
            else:
                raise ValueError("Unsupported archive format. Use .zip or .tar.gz")
    finally:
        os.remove(archive_path)


def traverse(d: Any, key_path: str, sep: str = ".", strict: bool = True) -> Any:
    """
    Retrieve a value from a nested Mapping-like object using a key path.

    If the object behaves like a Mapping (i.e., implements `__getitem__`),
    this function will be used to access elements.
    If it behaves like an object (i.e., `__getattr__`), the path will be
    resolved as attributes, instead.

    Parameters
    ----------
    d : dict
        The object to traverse.
    key_path : str
        A string representing the path of keys, separated by `sep`.
    sep : str, optional
        The separator used to split the key path into individual keys.
        Default is ".".
    strict : bool, optional
        If False, return None when a key in the path does not exist.
        If True, raise a KeyError when a key does not exist.
        Default is False.

    Returns
    -------
    Any
        The value at the specified key path, or None if a key is missing
        and `strict` is False.

    Raises
    ------
    KeyError
        If `strict` is True and any key in the path does not exist.

    Examples
    --------
    >>> d = {"foo": {"bar": {"baz": 42}}}
    >>> traverse(d, "foo.bar.baz")
    42

    >>> traverse(d, "foo.bar.qux", strict=False) is None
    True

    >>> traverse(d, "foo.bar.qux", strict=True)
    Traceback (most recent call last):
    ...
    KeyError: 'qux'
    """

    def has_item(container, key):
        if hasattr(container, "__contains__"):
            # Container behaves like a dict
            return key in container
        elif hasattr(container, key):
            # Container behaves like an object
            return True
        else:
            return False

    def get_item(container, key, default=None):
        if hasattr(container, "__getitem__"):
            # Container behaves like a dict
            try:
                return container[key]
            except (KeyError, IndexError, TypeError):
                return default
        elif hasattr(container, key):
            # Container behaves like an object
            return getattr(container, key, default)
        else:
            return default

    keys = key_path.split(sep)
    for key in keys:
        # Bail out on missing entries in strict mode
        if strict and not has_item(d, key):
            raise KeyError(key)

        d = get_item(d, key)
        if d is None:
            return None
    return d
