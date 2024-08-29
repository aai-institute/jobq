from collections.abc import Callable
from functools import wraps
from typing import Concatenate, ParamSpec, TypeVar

import openapi_client
from openapi_client.exceptions import ApiException

# TODO: Factor backend host url into some kind of config file
BACKEND_HOST = "http://localhost:8000"

T = TypeVar("T")
P = ParamSpec("P")


def _make_api_client() -> openapi_client.ApiClient:
    api_config = openapi_client.Configuration(host=BACKEND_HOST)
    return openapi_client.ApiClient(api_config)


def with_job_mgmt_api(
    func: Callable[Concatenate[openapi_client.JobManagementApi, P], T],
) -> Callable[P, T]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        with _make_api_client() as api:
            client = openapi_client.JobManagementApi(api)
            try:
                return func(client, *args, **kwargs)
            except openapi_client.ApiException as e:
                handle_api_exception(e, func.__name__)
                raise e

    return wrapper


def handle_api_exception(e: ApiException, op: str) -> None:
    print(f"Error executing {op}:")
    if e.status == 404:
        print("Workload not found. It may have been terminated or never existed.")
    else:
        print(f"Status: {e.status} - {e.reason}")
