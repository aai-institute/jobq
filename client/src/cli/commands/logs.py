import argparse
from enum import Enum
from typing import Any

import openapi_client
from cli.types import Settings
from cli.util import with_job_mgmt_api


class LogCommands(Enum):
    UID = "uid"
    TAIL = "tail"
    FOLLOW = "follow"

    def to_argparse(self) -> list[str]:
        if self.short_command:
            return [f"-{self.short_command}", f"--{self.value}"]
        else:
            return [f"--{self.value}"]

    @property
    def short_command(self) -> str | None:
        _short_commands = {
            "follow": "f",
        }
        return _short_commands.get(self.value, None)

    @classmethod
    def values(cls) -> list[str]:
        return [member.value for member in cls]


def sanitize_log_params(args: argparse.Namespace) -> dict[str, Any]:
    _param_map = {
        LogCommands.FOLLOW.value: "stream",
    }
    return {
        # translate argparse args to openapi_client params
        _param_map.get(k, k): v
        for k, v in vars(args).items()
        if v is not None and k in LogCommands.values()
    }


def stringify_dict(d: dict[str, Any]) -> dict[str, str]:
    return {k: str(v) for k, v in d.items()}


@with_job_mgmt_api
def logs(
    client: openapi_client.JobManagementApi,
    args: argparse.Namespace,
    settings: Settings,
) -> None:
    params = sanitize_log_params(args)
    resp = client.logs_jobs_uid_logs_get(**params)
    print(resp)


@with_job_mgmt_api
def stream_logs(
    client: openapi_client.JobManagementApi,
    args: argparse.Namespace,
    settings: Settings,
) -> None:
    params = sanitize_log_params(args)
    resp = client.logs_jobs_uid_logs_get_without_preload_content(**params)
    for line in resp.stream():
        print(line.decode("utf-8"), end="")


def handle_logs_cmd(args: argparse.Namespace, settings: Settings) -> None:
    if args.follow:
        stream_logs(args, settings=settings)
    else:
        logs(args, settings=settings)


def add_parser(subparsers: Any, parent: argparse.ArgumentParser) -> None:
    # jobq logs, command to fetch logs for workload
    help = "Get logs for specified job"
    parser = subparsers.add_parser(
        "logs",
        parents=[parent],
        help=help,
        description=help,
    )
    parser.add_argument(LogCommands.UID.value, metavar="<ID>")
    parser.add_argument(
        *LogCommands.FOLLOW.to_argparse(),
        action="store_true",
        help="Whether to stream logs",
    )
    parser.add_argument(
        *LogCommands.TAIL.to_argparse(),
        type=int,
        help="Lines of recent logs to display (default: -1, all lines)",
    )
    parser.set_defaults(func=handle_logs_cmd)
