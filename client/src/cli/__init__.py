import logging
import sys

import pydantic
from pydantic_settings import CliSettingsSource

import cli.parser
from cli.types import Settings


def _configure_logging(settings: Settings) -> None:
    logging.getLogger().setLevel(settings.log_level)


# kwargs are only used for testing with CliRunner
def main(**kwargs: str) -> None:
    """CLI entrypoint for job submission"""

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

    try:
        # Integrate CLI settings into the base parser used by all CLI subcommands and load settings
        # https://docs.pydantic.dev/latest/concepts/pydantic_settings/#integrating-with-existing-parsers

        # Note that the settings will be made available on the subcommands, rather than the root command.
        # Thus, one cannot invoke the CLI like so:
        #   jobq --cli-option=... <subcommand>

        cli.parser.init()
        cli_settings = CliSettingsSource(
            Settings,
            root_parser=cli.parser.parser,
            cli_exit_on_error=False,
            cli_parse_args=None,
            cli_hide_none_type=True,
        )
        parser = cli.parser.build_root_parser()
        func_args = parser.parse_args(kwargs.get("args"))

        try:
            settings = Settings(
                _cli_settings_source=cli_settings(parsed_args=func_args)
            )
            _configure_logging(settings)
            logging.debug(f"settings: {settings}")
        except pydantic.ValidationError as e:
            print("Invalid settings detected:", file=sys.stderr)
            for error in e.errors():
                print(
                    f"  - {error['loc'][0]}: {error['msg']} (got {error['input']!r})",
                    file=sys.stderr,
                )
            sys.exit(1)

        # this is the case of no command, but also no existing action
        # (like -h or --version) -> user error
        if not hasattr(func_args, "func"):
            raise ValueError("no subcommand specified")
        func_args.func(func_args, settings=settings)
        sys.exit(0)
    except Exception as e:
        print(f"error: {e}", file=sys.stderr)
        # FIXME: Exit with more nuanced error codes
        sys.exit(1)


# CLI name, so it can be used with Click's CliRunner for testing
name = "jobq"
