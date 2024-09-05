import logging
import os
import sys

from .parser import main_parser


def main(argv: list[str] | None = None) -> None:
    """CLI entrypoint for job submission"""

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("urllib3.connectionpool").setLevel(logging.INFO)

    try:
        args = main_parser().parse_args(argv)
        # this is the case of no command, but also no exiting action
        # (like -h or --version) -> user error
        if not hasattr(args, "func"):
            raise ValueError("no subcommand specified")
        args.func(args)
        sys.exit(0)
    except Exception as e:
        sys.stderr.write(f"error: {e}")
        sys.stderr.write(os.linesep)
        # FIXME: Exit with more nuanced error codes
        sys.exit(1)
