import argparse
import asyncio
from collections.abc import AsyncGenerator
from enum import Enum
from pprint import pp
from typing import Any
from urllib.parse import urljoin

import aiohttp

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


def sanitize_log_params(args: argparse.Namespace) -> dict[str, Any]:
    return {
        k: v
        for k, v in vars(args).items()
        if v is not None and k in LogCommands.values()
    }


def stringify_dict(d: dict[str, Any]) -> dict[str, str]:
    return {k: str(v) for k, v in d.items()}


@with_job_mgmt_api
def logs(client: openapi_client.JobManagementApi, args: argparse.Namespace) -> None:
    params = sanitize_log_params(args)
    resp = client.logs_jobs_uid_logs_get(**params)
    pp(resp)


async def async_generate_log_lines(
    client: openapi_client.JobManagementApi, params: dict
) -> AsyncGenerator[str, None]:
    url = urljoin(client.api_client.configuration.host, f"jobs/{params['uid']}/logs")
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=stringify_dict(params)) as response:
            async for line in response.content.iter_any():
                yield line.decode().strip()


async def print_streamed_log_lines(
    client: openapi_client.JobManagementApi, params: dict
) -> None:
    try:
        async for log_line in async_generate_log_lines(client, params):
            pp(log_line)
    except aiohttp.ClientResponseError as e:
        handle_api_exception(e, "log stream")
        raise


async def async_stream_logs(args: argparse.Namespace) -> None:
    params = sanitize_log_params(args)
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
