import argparse
from importlib.metadata import PackageNotFoundError, version

from cli.util import CustomFormatter

from .commands import list as _list
from .commands import logs, status, stop, submit

try:
    __version__ = version("aai-jobq")
except PackageNotFoundError:
    pass

# alphabetically sorted
COMMANDS = [_list, logs, status, stop, submit]


# Add a base parser that all subcommand parsers can "inherit" from.
# This eliminates the need to duplicate arguments for parsers.

MAIN_PARSER: argparse.ArgumentParser
parser: argparse.ArgumentParser


def init():
    global MAIN_PARSER, parser
    MAIN_PARSER = argparse.ArgumentParser(
        description="The jobq command-line interface",
        formatter_class=CustomFormatter,
    )
    parser = argparse.ArgumentParser(
        add_help=False,
        formatter_class=CustomFormatter,
    )


def build_root_parser() -> argparse.ArgumentParser:
    # Main parser, invoked when running `jobq <options>` , i.e. without a subcommand.
    # Since we pass required=True to the commands subparser below,
    # any action that does not immediately exit (like e.g. help and version do)
    # will prompt an error about requiring a subcommand.
    MAIN_PARSER.add_argument(
        "-v",
        "--version",
        action="version",
        help="show jobq version and exit",
        version=f"%(prog)s version {__version__}",
    )

    subparsers = MAIN_PARSER.add_subparsers(
        metavar="<command>",
        required=True,
        help="Commands",
    )

    for cmd in COMMANDS:
        cmd.add_parser(subparsers, parser)

    return MAIN_PARSER
