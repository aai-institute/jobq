import argparse
import asyncio
from collections.abc import AsyncGenerator
from enum import Enum
from pprint import pp
from typing import Any
from urllib.parse import urljoin

import httpx

import openapi_client

from .util import _make_api_client, handle_api_exception, with_job_mgmt_api


class LogCommands(Enum):
    NAMESPACE = "namespace"
    UID = "uid"
    TAIL = "tail"
    STREAM = "stream"

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]


def prepare_log_params(args: argparse.Namespace) -> dict:
    return {
        k: v
        for k, v in vars(args).items()
        if v is not None and k in LogCommands.values()
    }


@with_job_mgmt_api
def logs(client: openapi_client.JobManagementApi, args: argparse.Namespace) -> None:
    params = prepare_log_params(args)
    resp = client.logs_jobs_uid_logs_get(**params)
    pp(resp)


async def async_generate_log_lines(
    client: openapi_client.JobManagementApi, params: dict
) -> AsyncGenerator[str, None]:
    async with httpx.AsyncClient() as http_client:
        url = urljoin(
            client.api_client.configuration.host, f"jobs/{params['uid']}/logs"
        )
        async with http_client.stream("GET", url, params=params) as response:
            async for line in response.aiter_lines():
                yield line.strip()


async def print_streamed_log_lines(
    client: openapi_client.JobManagementApi, params: dict
) -> None:
    try:
        async for log_line in async_generate_log_lines(client, params):
            pp(log_line)
    except openapi_client.ApiException as e:
        handle_api_exception(e, "log stream")
        raise


async def async_stream_logs(args: argparse.Namespace) -> None:
    params = prepare_log_params(args)
    with _make_api_client() as api:
        client = openapi_client.JobManagementApi(api)
        await print_streamed_log_lines(client, params)


def handle_logs_cmd(args: argparse.Namespace) -> None:
    if args.stream:
        asyncio.run(async_stream_logs(args))
    else:
        logs(args)


def add_parser(subparsers: Any, parent: argparse.ArgumentParser) -> None:
    # jobby logs, command to fetch logs for workload
    parser = subparsers.add_parser("logs", description="Get logs for specified job.")
    parser.add_argument(
        f"--{LogCommands.NAMESPACE.value}",
        help="Kubernetes namespace the job was created in, "
        "defaults to currently active namespace.",
    )
    parser.add_argument(LogCommands.UID.value, metavar="<ID>")
    parser.add_argument(
        f"--{LogCommands.STREAM.value}",
        action="store_true",
        help="Whether to stream logs",
    )
    parser.add_argument(
        f"--{LogCommands.TAIL.value}",
        type=int,
        help="Lines of recent logs to display",
    )
    parser.set_defaults(func=handle_logs_cmd)
