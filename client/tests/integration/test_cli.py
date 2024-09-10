import pytest
from click.testing import CliRunner

import cli


@pytest.mark.parametrize("command", ["", "list", "logs", "status", "stop", "submit"])
@pytest.mark.parametrize("flag", ["-h", "--help"])
def test_help(command: str, flag: str) -> None:
    """Test that the help message is displayed correctly for all commands."""

    runner = CliRunner()
    result = runner.invoke(cli, [command, flag] if command else [flag])
    assert result.exit_code == 0
    assert "usage" in result.output
