import logging
import os
import sys

from .parser import main_parser


def main(**kwargs: str) -> None:
    """CLI entrypoint for job submission"""

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

    try:
        func_args = main_parser().parse_args(kwargs.get("args"))
        # this is the case of no command, but also no exiting action
        # (like -h or --version) -> user error
        if not hasattr(func_args, "func"):
            raise ValueError("no subcommand specified")
        func_args.func(func_args)
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"error: {e}")
        sys.stderr.write(os.linesep)
        # FIXME: Exit with more nuanced error codes
        sys.exit(1)


# CLI name, so it can be used with Click's CliRunner for testing
name = "jobby"
