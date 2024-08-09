from __future__ import annotations

import enum
import functools
import inspect
import io
import logging
import os
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Generic, ParamSpec, TypedDict, TypeVar

import docker.types

from jobs.assembler import config
from jobs.assembler.renderers import RENDERERS
from jobs.image import Image
from jobs.submission_context import SubmissionContext
from jobs.types import AnyPath, K8sResourceKind
from jobs.utils.helpers import remove_none_values
from jobs.utils.math import to_rational
from jobs.utils.processes import run_command


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


class RayResourceOptions(TypedDict, total=False):
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
class SchedulingOptions:
    priority_class: str | None = None
    """Kueue priority class name"""

    queue_name: str | None = None
    """Kueue local queue name"""


@dataclass(frozen=True)
class ImageOptions:
    name: str | None = None
    """Name of the image. If unspecified, inferred from the job."""

    tag: str = "latest"
    spec: Path | None = None
    dockerfile: Path | None = None
    build_context: Path = Path.cwd()

    @property
    def build_mode(self) -> BuildMode:
        if self.spec is not None:
            return BuildMode.YAML
        elif self.dockerfile is not None:
            return BuildMode.DOCKERFILE
        else:
            raise ValueError(
                "error building image: either YAML spec or Dockerfile must be set."
            )

    def _canonicalize(self, attr: str) -> Path | None:
        path = self.__getattribute__(attr)

        if path is None:
            return None

        if not isinstance(path, (str, Path)):
            raise TypeError(f"Expected {attr!r} to be a str or Path, got: {type(path)}")

        if isinstance(path, str):
            path = Path(path)

        canonical_path = path.resolve()
        object.__setattr__(self, attr, canonical_path)

        return canonical_path

    def __post_init__(self) -> None:
        def _is_yaml(path: AnyPath) -> bool:
            filename = os.path.basename(path)
            return filename.endswith((".yaml", ".yml"))

        self._canonicalize("dockerfile")
        self._canonicalize("build_context")
        self._canonicalize("spec")

        if self.spec is None and self.dockerfile is None:
            raise ValueError("Must specify either image spec or Dockerfile")

        if self.spec is not None and self.dockerfile is not None:
            raise ValueError("Cannot specify both image spec and Dockerfile")

        if self.spec is not None and not _is_yaml(self.spec):
            raise ValueError(f"Container image spec is not a YAML file: {self.spec}")

        if not self.build_context.is_dir():
            raise ValueError(f"Build context must be a directory: {self.build_context}")

        if self.dockerfile is not None and not self.dockerfile.is_relative_to(
            self.build_context
        ):
            raise ValueError(
                f"Dockerfile must be relative to build context {self.build_context}"
            )


@dataclass(frozen=True)
class JobOptions:
    resources: ResourceOptions | None = None
    """Resource requests for this job in Kubernetes format (see https://kubernetes.io/docs/concepts/configuration/manage-resources-containers/#resource-units-in-kubernetes)"""
    image: ImageOptions | None = None
    scheduling: SchedulingOptions | None = None
    labels: dict[str, str] = field(default_factory=dict)


P = ParamSpec("P")
T = TypeVar("T")


class Job(Generic[P, T]):
    def __init__(
        self,
        func: Callable[P, T],
        *,
        options: JobOptions | None = None,
        context: SubmissionContext | None = None,
    ) -> None:
        functools.update_wrapper(self, func)
        self._func = func
        self.options = options
        self.context = context or SubmissionContext()

        if (module := inspect.getmodule(self._func)) is None:
            raise ValueError("Cannot derive module for Job function.")

        self._name = self._func.__name__
        self._file = os.path.relpath(str(module.__file__))

        self.validate()

    @property
    def name(self) -> str:
        return self._name

    @property
    def file(self) -> str:
        return self._file

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self._func(*args, **kwargs)

    def _render_dockerfile(self) -> str:
        """Render the job's Dockerfile from a YAML spec."""

        if not (self.options and self.options.image):
            raise ValueError("Container image options must be specified")

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

    def validate(self) -> None:
        if self.options:
            validate_labels(self.options.labels)

    def build_image(
        self,
        push: bool = False,
    ) -> Image | None:
        if not self.options or not self.options.image:
            raise ValueError("Need image options to build image")
        opts = self.options.image

        tag = f"{opts.name or self.name}:{opts.tag}"

        logging.info(f"Building container image: {tag!r}")

        build_cmd = ["docker", "build", "-t", tag]
        build_cmd.extend([f"--label={k}={v}" for k, v in self.options.labels.items()])

        exit_code: int = -1
        if opts.build_mode == BuildMode.YAML:
            yaml = self._render_dockerfile()
            with io.StringIO(yaml) as dockerfile:
                build_cmd.extend(["-f-", f"{ opts.build_context.absolute() }"])
                exit_code, _, _, _ = run_command(
                    shlex.join(build_cmd),
                    stdin=dockerfile,
                    verbose=True,
                )
        elif opts.build_mode == BuildMode.DOCKERFILE:
            if opts.dockerfile is None:
                raise ValueError("Dockerfile path must be specified")
            if not opts.dockerfile.is_file():
                raise FileNotFoundError(
                    f"Specified Dockerfile not found: {opts.dockerfile.absolute()}"
                )
            build_cmd.extend(
                ["-f", f"{ opts.dockerfile }", f"{ opts.build_context.absolute() }"]
            )
            exit_code, _, _, _ = run_command(
                shlex.join(build_cmd),
                verbose=True,
            )

        if exit_code == 0:
            if push:
                logging.info("Pushing container image to remote registry")
                exit_code, _, _, _ = run_command(
                    f"docker push {tag}",
                    verbose=True,
                )
                if exit_code != 0:
                    return None

            return Image(tag)
        else:
            return None


def job(*, options: JobOptions | None = None) -> Callable[[Callable[P, T]], Job[P, T]]:
    def _wrapper(fn: Callable[P, T]) -> Job[P, T]:
        return Job(fn, options=options)

    return _wrapper


def validate_labels(labels: dict[str, str]) -> None:
    """Validate the syntactic correctness of user-specified job labels.

    Note that the rules for labels are the intersection (i.e., the strictest subset)
    of syntax restrictions on Docker labels and Kubernetes annotations, so that the
    labels can be applied in either context.

    See the following documents for further reference:
    - Docker: <https://docs.docker.com/config/labels-custom-metadata/#value-guidelines>
    - Kubernetes: <https://kubernetes.io/docs/concepts/overview/working-with-objects/annotations/#syntax-and-character-set>

    Raises
    ------
    ValueError
        if the labels are not well-formed
    """
    for k, v in labels.items():
        # Label keys:
        # - Must start and end with a letter
        # - Can contain dashes (-), underscores (_), dots (.), slashes (/), and alphanumerics between.
        # - May not contain prefixes (as used in Kubernetes), since they are not compatible with Docker
        if not re.match(r"^[a-z]+(?:[/._-][a-z0-9]+)*[a-z]?$", k):
            raise ValueError(f"Label key is not well-formed: {k}")

        # Label values:
        # - Maximum length of 127 characters
        if len(v) > 127:
            raise ValueError(f"Label value is not well-formed: {v}")
