import contextlib

import pytest

from jobs_server.models import validate_image_ref


@pytest.mark.parametrize(
    "ref, expected_error",
    [
        # --- Valid image references
        ("docker.io/library/ubuntu:latest", None),
        (
            "docker.io/library/ubuntu@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            None,
        ),
        ("quay.io/company/app:v1.0.0", None),
        ("registry.example.com/project/image:tag", None),
        ("localhost:5000/myapp:latest", None),
        ("image_name", None),  # missing tag is OK
        # --- Invalid image references
        ("", AssertionError),
        ("docker.io/", AssertionError),  # missing image name
        ("docker.io/library/", AssertionError),  # missing image name
        ("docker.io/library/ubuntu:", AssertionError),  # empty tag
        ("docker.io/library/ubuntu@", AssertionError),  # empty digest
        ("docker.io/library/ubuntu@sha256:", AssertionError),  # empty digest hash
        ("docker.io/library/ubuntu@sha256:0123456", AssertionError),  # hash too short
        (
            "http://docker.io/library/ubuntu:latest",
            AssertionError,
        ),  # invalid characters
        ("docker.io/library/ubuntu linux:tag", AssertionError),  # spaces in name
        ("docker.io/library/ubuntu:tag with spaces", AssertionError),  # spaces in tag
        (
            "docker.io/library/ubuntu@digest with spaces",
            AssertionError,
        ),  # spaces in digest
    ],
)
def test_image_ref_validation(ref: str, expected_error: type[Exception] | None) -> None:
    ctx = contextlib.nullcontext()
    if expected_error is not None:
        ctx = pytest.raises(expected_error)

    with ctx:
        validate_image_ref(ref)
