import contextlib

import pytest

from jobq.job import (
    Job,
    JobOptions,
    ResourceOptions,
    SchedulingOptions,
    validate_labels,
)


@pytest.mark.parametrize(
    ["opts", "expected_error"],
    [
        (JobOptions(scheduling=SchedulingOptions(queue_name="q")), None),
        (
            JobOptions(
                labels={"valid": "valid"}, scheduling=SchedulingOptions(queue_name="q")
            ),
            None,
        ),
        (
            JobOptions(
                labels={"invalid-": "valid"},
                scheduling=SchedulingOptions(queue_name="q"),
            ),
            ValueError,
        ),
    ],
)
def test_job_validation(
    opts: JobOptions, expected_error: type[Exception] | None
) -> None:
    """Exercise the constructor validation of job options"""

    # Assert validation error if specified in fixture
    exc_ctx = (
        pytest.raises(expected_error) if expected_error else contextlib.nullcontext()
    )
    with exc_ctx:
        _ = Job(lambda: ..., options=opts)


def test_resource_options_docker():
    opts = ResourceOptions(memory="1024Mi", cpu="200m")
    actual = opts.to_docker()

    assert actual["mem_limit"] == str(1024 * 2**20)
    assert actual["nano_cpus"] == int(0.2 * 10**9)


def test_resource_options_k8s():
    opts = ResourceOptions(memory="1024Mi", cpu="200m")
    actual = opts.to_kubernetes()

    assert actual["memory"] == opts.memory
    assert actual["cpu"] == opts.cpu


def test_resource_options_ray():
    opts = ResourceOptions(memory="1024Mi", cpu="2000m", gpu=1)
    actual = opts.to_ray()

    assert actual["entrypoint_memory"] == int(1024 * 2**20)
    assert actual["entrypoint_num_cpus"] == 2
    assert actual["entrypoint_num_gpus"] == 1


@pytest.mark.parametrize(
    "labels, expected_error",
    [
        ({"valid-key": "valid-value"}, None),
        ({"also_valid_key": "AlsoValidValue"}, None),
        ({"invalid key": "valid-value"}, "Label key is not well-formed: invalid key"),
        ({"valid-key": "valid!"}, None),
        ({"valid/key": "valid"}, None),
        ({"123invalid": "123-invalid"}, "Label key is not well-formed: 123invalid"),
        ({"invalid-": "123-invalid"}, "Label key is not well-formed: invalid-"),
        ({"invAlid": "valid"}, "Label key is not well-formed: invAlid"),
        ({"inv@lid": "valid"}, "Label key is not well-formed: inv@lid"),
        ({"valid": "v@lid"}, None),
        ({"a" * 63: "valid"}, None),
        ({"valid": "a" * 127}, None),
        ({"valid": "a" * 128}, "Label value is not well-formed: " + "a" * 128),
        ({"-invalid": "valid"}, "Label key is not well-formed: -invalid"),
        ({"valid": "-valid"}, None),
        ({"valid.key.with.dots": "valid.value.with.dots"}, None),
        ({"": ""}, "Label key is not well-formed: "),
        ({"invalid--key": "valid_value"}, "Label key is not well-formed: invalid--key"),
    ],
)
def test_validate_labels(labels, expected_error):
    if expected_error is None:
        validate_labels(labels)
    else:
        with pytest.raises(ValueError) as exc_info:
            validate_labels(labels)
        assert str(exc_info.value) == expected_error
