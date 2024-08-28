import argparse

from .commands import status, stop, submit

# FIXME: Source dynamically
__version__ = "0.1.0"

description = """
Available commands:

    status - Query the status of a previously submitted job.
    stop   - Terminate the execution of a previously submitted job.
    submit - Submit a job to a local Kueue job queue.
"""

# alphabetically sorted
COMMANDS = [status, stop, submit]


# FIXME: Top-level parser shows command names as positionals, remove!
class CustomFormatter(argparse.RawDescriptionHelpFormatter):
    def _format_action_invocation(self, action):
        if not action.option_strings:
            (metavar,) = self._metavar_formatter(action, action.dest)(1)
            return metavar
        else:
            parts = []
            # if the Optional doesn't take a value, format is:
            #    -s, --long
            if action.nargs == 0:
                parts.extend(action.option_strings)

            # if the Optional takes a value, format is:
            #    -s, --long ARGS
            else:
                default = action.dest.upper()
                args_string = self._format_args(action, default)
                parts.extend(action.option_strings)
                parts[-1] += f" {args_string}"
            return ", ".join(parts)


def main_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        add_help=False,
        prog="jobby",
        usage="jobby",  # TODO: This does not format well with subcommands
        description=description,
        formatter_class=CustomFormatter,
    )

    # FIXME: The fact that this appears top-level means that
    #  subparsers cannot add a command-level help, which sucks
    #  -> refactor "jobby" into another subparser
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this message and exit.",
    )

    parser.add_argument(
        "-v",
        action="store_true",
        default=False,
        dest="verbose",
        help="Enable verbose mode.",
    )

    parser.add_argument(
        "-q",
        action="store_true",
        default=False,
        dest="verbose",
        help="Enable quiet mode.",
    )

    parser.add_argument(
        "--version",
        action="version",
        help="Show jobby version and exit.",
        version=f"%(prog)s version {__version__}",
    )

    subparsers = parser.add_subparsers(title="subcommands", required=False)

    for cmd in COMMANDS:
        cmd.add_parser(subparsers, parser)

    return parser
