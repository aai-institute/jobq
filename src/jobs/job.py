import enum
import functools
import inspect
import logging
import os
import pathlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

import docker
import docker.types

from jobs.assembler import config
from jobs.assembler.renderers import RENDERERS
from jobs.image import Image
from jobs.util import remove_none_values, to_rational

WORKING_DIRECTORY = "."


class BuildMode(enum.Enum):
    YAML = "yaml"
    DOCKERFILE = "dockerfile"

    @classmethod
    def _print_values(cls) -> str:
        return ", ".join(entry.value for entry in cls)


@dataclass(frozen=True)
class ResourceOptions:
    memory: str | None = None
    cpu: str | None = None
    gpu: int | None = None

    def to_docker(self) -> dict[str, Any]:
        return remove_none_values(
            {
                "mem_limit": str(int(to_rational(self.memory))),
                "nano_cpus": int(to_rational(self.cpu) * 10**9),
                "device_requests": (
                    [
                        docker.types.DeviceRequest(
                            capabilities=[["gpu"]],
                            count=self.gpu,
                        )
                    ]
                    if self.gpu
                    else None
                ),
            }
        )

    def to_kubernetes(
        self, kind: Literal["requests", "limits"] = "requests"
    ) -> dict[str, str]:
        if kind == "requests":
            return remove_none_values(
                {
                    "cpu": self.cpu,
                    "memory": self.memory,
                    "nvidia.com/gpu": self.gpu,
                }
            )
        elif kind == "limits":
            return remove_none_values({"nvidia.com/gpu": self.gpu})

    def to_ray(self) -> dict[str, Any]:
        return remove_none_values(
            {
                "entrypoint_memory": int(to_rational(self.memory)),
                "entrypoint_num_cpus": int(to_rational(self.cpu)),
                "entrypoint_num_gpus": self.gpu,
            }
        )


@dataclass(frozen=True)
class ImageOptions:
    spec: os.PathLike[str] | str
    name: str | None = None
    tag: str = "latest"
    build_context: str = WORKING_DIRECTORY
    build_mode: Literal[BuildMode.YAML, BuildMode.DOCKERFILE] = field(init=False)

    def __post_init__(self) -> None:
        def _is_yaml(path: os.PathLike[str]) -> bool:
            filename = os.path.basename(path)
            return filename.endswith((".yaml", ".yml"))

        object.__setattr__(
            self,
            "build_mode",
            BuildMode.YAML if _is_yaml(self.spec) else BuildMode.DOCKERFILE,
        )

        if isinstance(self.spec, str):
            object.__setattr__(self, "spec", Path(self.spec))


@dataclass(frozen=True)
class JobOptions:
    resources: ResourceOptions | None
    """Resource requests for this job in Kubernetes format (see https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/#resource-units-in-kubernetes)"""
    image: ImageOptions | None


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

    def _image_from_yaml(self) -> None:
        image_cfg = config.load_config(self.options.image.spec)

        renderers = [cls(image_cfg) for cls in RENDERERS if cls.accepts(image_cfg)]
        dockerfile_content = ""
        for r in renderers:
            dockerfile_content += r.render() + "\n"
        logging.debug(dockerfile_content)
        # dockerfile = BytesIO(dockerfile_content.encode("utf-8"))
        # TODO: Fix this hacky saving of the dockerfile, which may overwrite existing files
        # and results in artifacts.
        pathlib.Path("Dockerfile").write_text(dockerfile_content)

    def build_image(
        self,
    ) -> Image:
        if not self.options or not self.options.image:
            raise ValueError("Need image options to build image")
        if self.options.image.build_mode == BuildMode.YAML:
            self._image_from_yaml()
        elif self.options.image.build_mode == BuildMode.DOCKERFILE:
            pass
        else:
            raise ValueError(
                f"argument `src` must be one of {BuildMode._print_values()}"
            )
        opts = self.options.image
        client = docker.from_env()
        client.images.build(
            tag=f"{opts.name or self.name}:{opts.tag}", path=opts.build_context
        )
        return Image(f"{opts.name or self.name}:{opts.tag}")


def job(fn: Callable | None = None, options: JobOptions | None = None):
    if fn is None:
        return functools.partial(job, options=options)
    return Job(fn, options=options)
