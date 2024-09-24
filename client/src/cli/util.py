import argparse
from collections.abc import Callable
from functools import wraps
from typing import Concatenate, ParamSpec, TypeVar, cast

import openapi_client
from cli.types import Settings
from openapi_client.exceptions import ApiException

T = TypeVar("T")
P = ParamSpec("P")


def _make_api_client(api_base_url: str) -> openapi_client.ApiClient:
    api_config = openapi_client.Configuration(host=api_base_url.removesuffix("/"))
    return openapi_client.ApiClient(api_config)


def with_job_mgmt_api(
    func: Callable[Concatenate[openapi_client.JobManagementApi, P], T],
) -> Callable[P, T]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        settings = cast(Settings, kwargs["settings"])
        with _make_api_client(str(settings.api_base_url)) as api:
            client = openapi_client.JobManagementApi(api)
            try:
                return func(client, *args, **kwargs)
            except openapi_client.ApiException as e:
                handle_api_exception(e, func.__name__)
                raise

    return wrapper


def handle_api_exception(e: ApiException, op: str) -> None:
    print(f"Error executing {op}:")
    if e.status == 404:
        print("Workload not found. It may have been terminated or never existed.")
    else:
        print(f"Status: {e.status} - {e.reason}")


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
