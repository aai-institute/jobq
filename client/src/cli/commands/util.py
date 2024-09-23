from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any, Concatenate, ParamSpec, TypeVar, cast

import yaml

import openapi_client
from openapi_client.exceptions import ApiException

DEFAULT_CONFIG = {"backend": {"host": "http://localhost:8000"}}
CONFIG_PATH = Path.home() / ".config" / "jobq" / "config.yaml"


C = TypeVar("C", bound="Config")


class Config:
    _instance: Config | None = None
    data: dict[str, Any]

    def __new__(cls: type[C]) -> C:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.data = cls._instance.load()
        return cast(C, cls._instance)

    def load(self) -> dict[str, Any]:
        if CONFIG_PATH.exists():
            return yaml.safe_load(CONFIG_PATH.read_text())
        return DEFAULT_CONFIG.copy()

    def save(self) -> None:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(yaml.dump(self.data))

    def get(self, key: str) -> Any:
        keys = key.split(".")
        value = self.data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                raise ValueError(f"Didnot find {key} in config")
        return value

    def set(self, key: str, value: str) -> None:
        keys = key.split(".")
        data = self.data
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]
        data[keys[-1]] = value
        self.save()


T = TypeVar("T")
P = ParamSpec("P")


def _make_api_client() -> openapi_client.ApiClient:
    api_config = openapi_client.Configuration(host=Config().get("backend.host"))
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
                raise

    return wrapper


def handle_api_exception(e: ApiException, op: str) -> None:
    print(f"Error executing {op}:")
    if e.status == 404:
        print("Workload not found. It may have been terminated or never existed.")
    else:
        print(f"Status: {e.status} - {e.reason}")
