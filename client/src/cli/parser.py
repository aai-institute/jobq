import argparse
from importlib.metadata import PackageNotFoundError, version

from .commands import status, stop, submit

try:
    __version__ = version("job-queue")
except PackageNotFoundError:
    pass

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
    # Add a base parser that all subcommand parsers can "inherit" from.
    # This eliminates the need to duplicate arguments for parsers.
    # TODO(nicholasjng): Add a k8s base parser inheriting all common k8s arguments
    #  (namespace, config, ...)
    base_parser = argparse.ArgumentParser(add_help=False)
    base_parser.add_argument(
        "-v",
        action="store_true",
        default=False,
        dest="verbose",
        help="Enable verbose mode.",
    )
    base_parser.add_argument(
        "-q",
        action="store_true",
        default=False,
        dest="verbose",
        help="Enable quiet mode.",
    )

    # Main parser, invoked when running `jobby <options>` , i.e. without a subcommand.
    # Since we pass required=True to the commands subparser below,
    # any action that does not immediately exit (like e.g. help and version do)
    # will prompt an error about requiring a subcommand.
    parser = argparse.ArgumentParser(
        add_help=False,
        prog="jobby",
        parents=[base_parser],
        description=description,
        formatter_class=CustomFormatter,
    )
    parser.add_argument(
        "-h",
        "--help",
        action="help",
        default=argparse.SUPPRESS,
        help="Show this message and exit.",
    )
    parser.add_argument(
        "--version",
        action="version",
        help="Show jobby version and exit.",
        version=f"%(prog)s version {__version__}",
    )

    subparsers = parser.add_subparsers(
        title="subcommands", metavar="<command>", required=True
    )

    for cmd in COMMANDS:
        cmd.add_parser(subparsers, base_parser)

    return parser
