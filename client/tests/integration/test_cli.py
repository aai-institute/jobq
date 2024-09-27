import pytest
from click.testing import CliRunner

import cli


@pytest.fixture(scope="module")
def runner() -> CliRunner:
    return CliRunner()


@pytest.mark.parametrize("command", ["", "list", "logs", "status", "stop", "submit"])
@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help(runner: CliRunner, command: str, flag: str) -> None:
    """Test that the help message is displayed correctly for all commands."""

    result = runner.invoke(cli, [command, flag] if command else [flag])

    if result.exit_code != 0:
        print(result.output)  # aid debugging in CI

    assert result.exit_code == 0
    assert "usage" in result.output
