import functools
import inspect
import os
from dataclasses import dataclass
from typing import Any, Callable

import docker.types

from jobs.util import to_rational


def _remove_none(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


@dataclass(frozen=True)
class ResourceOptions:
    memory: str | None = None
    cpu: str | None = None
    gpu: int | None = None

    def to_docker(self) -> dict[str, Any]:
        return _remove_none(
            {
                "mem_limit": str(int(to_rational(self.memory))),
                "nano_cpus": int(to_rational(self.cpu) * 10**9),
                "device_requests": docker.types.DeviceRequest(
                    device_ids=list(range(self.gpu))
                )
                if self.gpu
                else None,
            }
        )

    def to_kubernetes(self) -> dict[str, str]:
        return _remove_none(
            {
                "cpu": self.cpu,
                "memory": self.memory,
                "nvidia.com/gpu": self.gpu,
            }
        )

    def to_ray(self) -> dict[str, Any]:
        return _remove_none(
            {
                "entrypoint_memory": int(to_rational(self.memory)),
                "entrypoint_num_cpus": int(to_rational(self.cpu)),
                "entrypoint_num_gpus": self.gpu,
            }
        )


@dataclass(frozen=True)
class JobOptions:
    resources: ResourceOptions | None
    """Resource requests for this job in Kubernetes format (see https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/#resource-units-in-kubernetes)"""


class Job:
    def __init__(
        self, func: Callable | None = None, *, options: JobOptions | None = None
    ) -> None:
        functools.update_wrapper(self, func)
        self._func = func
        self.options = options

        module = inspect.getmodule(self._func)

        self._name = self._func.__name__
        self._file = os.path.relpath(str(module.__file__))

    @property
    def name(self) -> str:
        return self._name

    @property
    def file(self) -> str:
        return self._file

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self._func(*args, **kwargs)


def job(fn: Callable | None = None, options: JobOptions | None = None):
    if fn is None:
        return functools.partial(job, options=options)
    return Job(fn, options=options)
