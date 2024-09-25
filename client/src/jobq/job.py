from __future__ import annotations

import enum
import functools
import inspect
import io
import json
import logging
import pprint
import re
import shlex
from collections.abc import Callable
from collections.abc import Set as AbstractSet
from pathlib import Path
from typing import Any, ClassVar, Generic, ParamSpec, TypedDict, TypeVar

import docker.types
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr
from typing_extensions import Self

from jobq.assembler import config
from jobq.assembler.renderers import RENDERERS
from jobq.image import Image
from jobq.types import AnyPath, DictSerializable, JsonSerializable, K8sResourceKind
from jobq.utils.helpers import remove_none_values
from jobq.utils.math import to_rational
from jobq.utils.processes import run_command


class BuildMode(enum.Enum):
    YAML = "yaml"
    DOCKERFILE = "dockerfile"


class ImageOptions(BaseModel):
    """
    Options to configure the build of the Docker image used to execute a
    ``jobq.Job`` in the cluster.

    Either the ``spec`` argument or the ``dockerfile`` argument must be
    given, and if given, ``spec`` must be an existing file containing
    valid YAML.
    """

    name: StrictStr | None = None
    """The name under which the image should be pushed to the cluster image registry."""
    tag: StrictStr | None = "latest"
    """The tag identifier to use for the newly built Docker image."""
    spec: Path | None = None
    """Path to a YAML spec file describing a Docker image build."""
    dockerfile: Path | None = None
    """Path to an existing Dockerfile to use for the image build."""

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

    def model_post_init(self, /, __context: Any) -> None:
        def _is_yaml(path: AnyPath) -> bool:
            filename = Path(path).name
            return filename.endswith((".yaml", ".yml"))

        if self.spec is None and self.dockerfile is None:
            raise ValueError("Must specify either image spec or Dockerfile")

        if self.spec is not None and self.dockerfile is not None:
            raise ValueError("Cannot specify both image spec and Dockerfile")

        if self.spec is not None and not _is_yaml(self.spec):
            raise ValueError(f"Container image spec is not a YAML file: {self.spec}")


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


class ResourceOptions(JsonSerializable, DictSerializable, BaseModel):
    """
    Options for requesting cluster compute resources for a ``jobq.Job``.

    Memory and CPU values need to be given as ``<num> <prefix>``, where num
    is a floating point number, and prefix is one of the following SI metric
    prefixes:
        * ``m, k, M, G, T`` (base 10)
        * ``Ki, Mi, Gi, Ti`` (base 2).
    """

    memory: StrictStr | None = None
    """Memory required for pods hosting the job."""
    cpu: StrictStr | None = None
    """CPUs to request for pods hosting the job."""
    gpu: StrictInt | None = None
    """GPUs to request for pods hosting the job."""
    __properties: ClassVar[list[str]] = ["memory", "cpu", "gpu"]

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        protected_namespaces=(),
    )

    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

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


class SchedulingOptions(BaseModel):
    """
    Options configuring a ``jobq.Job``'s priority in the cluster, and
    the Kueue cluster queue name the job should be submitted to.
    """

    priority_class: StrictStr | None = None
    """Name of a Kueue priority class to use for the job. Must exist in the target cluster."""
    queue_name: StrictStr
    """The Kueue cluster queue name to submit the job to. Must refer to an existing queue
     in the cluster, otherwise the resulting workload will be marked inadmissible."""
    __properties: ClassVar[list[str]] = ["priority_class", "queue_name"]

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        protected_namespaces=(),
    )

    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))

    def to_json(self) -> str:
        """Returns the JSON representation of the model using alias"""
        # TODO: pydantic v2: use .model_dump_json(by_alias=True, exclude_unset=True) instead
        return json.dumps(self.to_dict())

    @classmethod
    def from_json(cls, json_str: str) -> Self | None:
        """Create an instance of SchedulingOptions from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        excluded_fields: AbstractSet[str] = set()

        _dict = self.model_dump(
            by_alias=True,
            exclude=excluded_fields,
            exclude_none=True,
        )
        # set to None if priority_class (nullable) is None
        # and model_fields_set contains the field
        if self.priority_class is None and "priority_class" in self.model_fields_set:
            _dict["priority_class"] = None

        # set to None if queue_name (nullable) is None
        # and model_fields_set contains the field
        if self.queue_name is None and "queue_name" in self.model_fields_set:
            _dict["queue_name"] = None

        return _dict

    @classmethod
    def from_dict(cls, obj: dict[str, Any] | None) -> Self | None:
        """Create an instance of SchedulingOptions from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate({
            "priority_class": obj.get("priority_class"),
            "queue_name": obj.get("queue_name"),
        })
        return _obj


class JobOptions(JsonSerializable, DictSerializable, BaseModel):
    """
    Options for customizing a Kubernetes job definition from a Python function.
    """

    resources: ResourceOptions | None = None
    """Compute resources to request for the job."""
    scheduling: SchedulingOptions
    """Information about the Kueue cluster queue, and job priority."""
    labels: dict[str, StrictStr] = Field(default_factory=dict)
    """Kubernetes labels to attach to the resulting Kueue workload."""
    __properties: ClassVar[list[str]] = ["resources", "scheduling", "labels"]

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=True,
        protected_namespaces=(),
    )

    def to_str(self) -> str:
        """Returns the string representation of the model using alias"""
        return pprint.pformat(self.model_dump(by_alias=True))


P = ParamSpec("P")
T = TypeVar("T")


class Job(Generic[P, T]):
    def __init__(
        self,
        func: Callable[P, T],
        *,
        options: JobOptions | None = None,
        image: ImageOptions | None = None,
        build_context: Path | None = None,
    ) -> None:
        functools.update_wrapper(self, func)
        self._func = func
        self.options = options
        self.image = image

        if (module := inspect.getmodule(self._func)) is None:
            raise ValueError("Cannot derive module for Job function.")

        job_file = Path(str(module.__file__))
        self._name = self._func.__name__
        self.build_context = (
            build_context
            if build_context is not None
            else self._resolve_build_context(job_file)
        )
        self._file = job_file.relative_to(self.build_context)
        self.validate()

    def _resolve_build_context(self, job_file: Path) -> Path:
        max_depth = 15
        build_context = job_file.resolve()
        for _ in range(max_depth):
            if self._is_project_root(build_context):
                break
            build_context = build_context.parent
        else:
            raise ValueError(
                f"Could not resolve build context from job file {self._file}, traversed {max_depth} up."
            )
        return build_context

    @classmethod
    def _is_project_root(cls, path: Path) -> bool:
        indicators = [
            ".git",
            "pyproject.toml",
            "setup.py",
        ]
        return any((path / indicator).exists() for indicator in indicators)

    @property
    def name(self) -> str:
        return self._name

    @property
    def file(self) -> str:
        return str(self._file)

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        return self._func(*args, **kwargs)

    def _resolve_path_in_build_context(self, path: Path) -> Path:
        if self.build_context is None:
            raise ValueError("Build context not resolved")

        resolved_path = self.build_context / path

        if not resolved_path.is_file():
            raise FileNotFoundError(
                f"Could not resolve path {path!r}. Path must be relative to resolved build context, {self.build_context!r}",
                resolved_path,
            )

        return resolved_path

    def _render_dockerfile(self) -> str:
        """Render the job's Dockerfile from a YAML spec."""

        if not (self.image):
            raise ValueError("Container image options must be specified")

        if not self.image.spec:
            raise ValueError("Container image spec must be specified")

        image_spec = self._resolve_path_in_build_context(self.image.spec)

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
        if not self.image:
            raise ValueError("Need image options to build image")
        opts = self.image

        tag = f"{opts.name or self.name}:{opts.tag}"

        logging.info(f"Building container image: {tag!r}")

        build_cmd = ["docker", "build", "-t", tag]
        labels = self.options.labels if self.options else {}
        build_cmd.extend([f"--label={k}={v}" for k, v in labels.items()])

        exit_code: int = -1
        if opts.build_mode == BuildMode.YAML:
            yaml = self._render_dockerfile()
            with io.StringIO(yaml) as dockerfile:
                build_cmd.extend(["-f-", f"{self.build_context.absolute()}"])
                exit_code, _, _, _ = run_command(
                    shlex.join(build_cmd),
                    stdin=dockerfile,
                    verbose=True,
                )
        elif opts.build_mode == BuildMode.DOCKERFILE:
            if not opts.dockerfile:
                raise ValueError("Dockerfile path must be specified")
            build_cmd.extend([
                "-f",
                f"{self._resolve_path_in_build_context(opts.dockerfile)}",
                f"{self.build_context.absolute()}",
            ])
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


def job(
    *,
    options: JobOptions | None = None,
    image: ImageOptions | None = None,
) -> Callable[[Callable[P, T]], Job[P, T]]:
    """
    A decorator to declare a Python function as a Kubernetes job,
    to be packaged and sent to a Kueue cluster queue for execution.

    Parameters
    ----------
    options: JobOptions | None
        Additional options to customize the job with. The given options
        influence scheduling, resource allocation for the job in the cluster,
        and labels to identify the job with.
    image: ImageOptions | None
        Options for customizing the Docker image build. Includes the image name,
        tag, and either a YAML spec file to build a Dockerfile from, or
        alternatively, a path to a pre-existing Dockerfile.

    Returns
    -------
    Job
        The actual Job instance wrapping the decorated function.

    """

    def _wrapper(fn: Callable[P, T]) -> Job[P, T]:
        return Job(
            fn,
            options=options,
            image=image,
        )

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
