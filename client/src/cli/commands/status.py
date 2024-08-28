import argparse
from argparse import ArgumentParser
from pprint import pp
from typing import Any

import openapi_client
import openapi_client.configuration
from openapi_client import ApiException

from .util import _make_api_client, handle_api_exception


def status(args: argparse.Namespace) -> None:
    with _make_api_client() as api:
        client = openapi_client.JobManagementApi(api)
        try:
            resp = client.status_jobs_uid_status_get(
                uid=args.uid,
                namespace=args.namespace,
            )
            pp(resp)
        except ApiException as e:
            handle_api_exception(e, "status check")


def add_parser(subparsers: Any, parent: ArgumentParser) -> None:
    # jobby status, the status querying command
    parser: argparse.ArgumentParser = subparsers.add_parser(
        "status",
        description="Query the status of a previously dispatched job.",
    )

    # unique identifier of the job
    parser.add_argument("uid", metavar="<ID>")
    parser.add_argument(
        "--namespace",
        help="Kubernetes namespace the job was created in, "
        "defaults to currently active namespace.",
    )
    # TODO: Factor out into command class
    parser.set_defaults(func=status)
