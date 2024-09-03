import argparse
from typing import Any


def list_workloads(args: argparse.Namespace) -> None:
    pass


def add_parser(subparsers: Any, parent: argparse.ArgumentParser) -> None:
    # jobby status, the status querying command
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "list",
        parents=[parent],
        description="List all previously dispatched jobs.",
    )

    # unique identifier of the job
    parser.add_argument(
        "--limit",
        metavar="<N>",
        default=None,
        help="Limit the listing to only a number of the most recent workloads.",
    )
    parser.add_argument(
        "--filter",
        metavar="<cond>",
        action="append",
        help="Filter existing workloads by a condition of the form <key>=<value> "
             "(e.g. status='succeeded'). Can be supplied multiple times for multiple "
             "conditions.",
    )
    parser.set_defaults(func=list_workloads)
