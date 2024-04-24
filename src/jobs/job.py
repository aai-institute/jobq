from __future__ import annotations

import enum
import functools
import inspect
import io
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, TypedDict

import docker.types

from jobs.assembler import config
from jobs.assembler.renderers import RENDERERS
from jobs.image import Image
from jobs.types import AnyPath, K8sResourceKind
from jobs.util import remove_none_values, run_command, to_rational


class BuildMode(enum.Enum):
    YAML = "yaml"
    DOCKERFILE = "dockerfile"


class DockerResourceOptions(TypedDict):
    mem_limit: str | None
    nano_cpus: float | None
    device_requests: list[docker.types.DeviceRequest] | None


# Functional definition of TypedDict to enable special characters in dict keys
K8sResourceOptions = TypedDict(
    "K8sResourceOptions",
    {
        "cpu": str | None,
        "memory": str | None,
        "nvidia.com/gpu": int | None,
    },
    total=False,
)


class RayResourceOptions(TypedDict):
    entrypoint_memory: int | None
    entrypoint_num_cpus: int | None
    entrypoint_num_gpus: int | None


@dataclass(frozen=True)
class ResourceOptions:
    memory: str | None = None
    cpu: str | None = None
    gpu: int | None = None

    def to_docker(self) -> DockerResourceOptions:
        options: DockerResourceOptions = {
            "mem_limit": str(int(to_rational(self.memory))) if self.memory else None,
            "nano_cpus": int(to_rational(self.cpu) * 10**9) if self.cpu else None,
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
        return remove_none_values(options)

    def to_kubernetes(
        self, kind: K8sResourceKind = K8sResourceKind.REQUESTS
    ) -> K8sResourceOptions:
        # TODO: Currently kind is not accessed and the logic for "request" and "limit" is the same.
        # Down the road we have to decide if we want to keep it that way (and get rid of the distinction and arguments),
        # or if it makes sense for us to distinguish both cases.
        options: K8sResourceOptions = {
            "cpu": self.cpu or None,
            "memory": self.memory or None,
            "nvidia.com/gpu": self.gpu or None,
        }
        return remove_none_values(options)

    def to_ray(self) -> RayResourceOptions:
        options: RayResourceOptions = {
            "entrypoint_memory": int(to_rational(self.memory)) if self.memory else None,
            "entrypoint_num_cpus": int(to_rational(self.cpu)) if self.cpu else None,
            "entrypoint_num_gpus": self.gpu or None,
        }
        return remove_none_values(options)


@dataclass(frozen=True)
class ImageOptions:
    name: str | None = None
    """Name of the image. If unspecified, inferred from the job."""

    tag: str = "latest"
    spec: AnyPath | None = None
    dockerfile: AnyPath | None = None
    build_context: AnyPath = Path.cwd()

    @property
    def build_mode(self) -> BuildMode:
        if self.spec:
            return BuildMode.YAML
        elif self.dockerfile:
            return BuildMode.DOCKERFILE
        else:
            raise ValueError("Unkown build mode, spec or dockerfile must be set.")

    def _to_pathlib(self, attr: str) -> None:
        val = self.__getattribute__(attr)
        if isinstance(val, str):
            object.__setattr__(self, attr, Path(val).absolute())

    def __post_init__(self) -> None:
        def _is_yaml(path: AnyPath) -> bool:
            filename = os.path.basename(path)
            return filename.endswith((".yaml", ".yml"))

        self._to_pathlib("dockerfile")
        self._to_pathlib("build_context")
        self._to_pathlib("spec")

        if not self.spec and not self.dockerfile:
            raise ValueError("Must specify either image spec or Dockerfile")

        if self.spec and self.dockerfile:
            raise ValueError("Cannot specify both image spec and Dockerfile")

        if self.spec and not _is_yaml(self.spec):
            raise ValueError(f"Container image spec is not a YAML file: {self.spec}")

        if not Path(self.build_context).is_dir():
            raise ValueError(f"Build context must be a directory: {self.build_context}")

        if self.dockerfile and not Path(self.dockerfile).is_relative_to(
            self.build_context
        ):
            raise ValueError("Dockerfile must be relative to build context")


@dataclass(frozen=True)
class JobOptions:
    resources: ResourceOptions | None
    """Resource requests for this job in Kubernetes format (see https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/#resource-units-in-kubernetes)"""
    image: ImageOptions | None


class Job:
    def __init__(self, func: Callable, *, options: JobOptions | None = None) -> None:
        functools.update_wrapper(self, func)
        self._func = func
        self.options = options

        if (module := inspect.getmodule(self._func)) is None:
            raise ValueError("Cannot derive module for Job function.")

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

    def _render_dockerfile(self) -> str:
        """Render the job's Dockerfile from a YAML spec."""

        image_spec = self.options.image.spec
        if not image_spec:
            raise ValueError("Container image spec must be specified")

        if not image_spec.is_file():
            raise FileNotFoundError(
                f"Container image spec file not found: {image_spec.is_file()}"
            )

        image_cfg = config.load_config(image_spec)

        renderers = [cls(image_cfg) for cls in RENDERERS if cls.accepts(image_cfg)]
        dockerfile_content = ""
        for r in renderers:
            dockerfile_content += r.render() + "\n"
        return dockerfile_content

    def build_image(
        self,
    ) -> Image | None:
        if not self.options or not self.options.image:
            raise ValueError("Need image options to build image")
        opts = self.options.image

        tag = f"{opts.name or self.name}:{opts.tag}"

        exit_code: int = -1
        if opts.build_mode == BuildMode.YAML:
            with io.StringIO(self._render_dockerfile()) as dockerfile:
                exit_code, _, _, _ = run_command(
                    f"docker build -t {tag} -f- {opts.build_context.absolute()}",
                    stdin=dockerfile,
                    verbose=True,
                )
        elif opts.build_mode == BuildMode.DOCKERFILE:
            if not opts.dockerfile.is_file():
                raise FileNotFoundError(
                    f"Specified Dockerfile not found: {opts.dockerfile.absolute()}"
                )
            exit_code, _, _, _ = run_command(
                f"docker build -t {tag} -f{opts.dockerfile} {opts.build_context.absolute()}",
                verbose=True,
            )

        if exit_code == 0:
            return Image(tag)
        else:
            return None


def job(fn: Callable | None = None, options: JobOptions | None = None):
    if fn is None:
        return functools.partial(job, options=options)
    return Job(fn, options=options)
