from __future__ import annotations

import enum
import functools
import inspect
import io
import json
import logging
import os
import pprint
import re
import shlex
from collections.abc import Set
from pathlib import Path
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Generic,
    List,
    Optional,
    ParamSpec,
    TypedDict,
    TypeVar,
)

import docker.types
from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr
from typing_extensions import Self

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


class ImageOptions(BaseModel):
    """
    ImageOptions
    """  # noqa: E501

    name: Optional[StrictStr] = None
    tag: Optional[StrictStr] = "latest"
    spec: Optional[Path] = None
    dockerfile: Optional[Path] = None
    build_context: Path = (
        Path.cwd()
    )  # FIXME: Maybe don't have a default here but rather only set it at build time
    __properties: ClassVar[List[str]] = [
        "name",
        "tag",
        "spec",
        "dockerfile",
        "build_context",
    ]

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
    def from_json(cls, json_str: str) -> Optional[Self]:
        """Create an instance of ImageOptions from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        excluded_fields: Set[str] = set([])

        _dict = self.model_dump(
            by_alias=True,
            exclude=excluded_fields,
            exclude_none=True,
        )
        # set to None if name (nullable) is None
        # and model_fields_set contains the field
        if self.name is None and "name" in self.model_fields_set:
            _dict["name"] = None

        # set to None if spec (nullable) is None
        # and model_fields_set contains the field
        if self.spec is None and "spec" in self.model_fields_set:
            _dict["spec"] = None

        # set to None if dockerfile (nullable) is None
        # and model_fields_set contains the field
        if self.dockerfile is None and "dockerfile" in self.model_fields_set:
            _dict["dockerfile"] = None

        return _dict

    @classmethod
    def from_dict(cls, obj: Optional[Dict[str, Any]]) -> Optional[Self]:
        """Create an instance of ImageOptions from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate(
            {
                "name": obj.get("name"),
                "tag": obj.get("tag") if obj.get("tag") is not None else "latest",
                "spec": obj.get("spec"),
                "dockerfile": obj.get("dockerfile"),
                "build_context": obj.get("build_context")
                if obj.get("build_context") is not None
                else "/Users/adriano/work/docker-job-poc/backend",
            }
        )
        return _obj

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

    # FIXME: This needs to be updated for Pydantic (since it doesn't call __post_init__ by default)
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


class ResourceOptions(BaseModel):
    """
    ResourceOptions
    """  # noqa: E501

    memory: Optional[StrictStr] = None
    cpu: Optional[StrictStr] = None
    gpu: Optional[StrictInt] = None
    __properties: ClassVar[List[str]] = ["memory", "cpu", "gpu"]

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
    def from_json(cls, json_str: str) -> Optional[Self]:
        """Create an instance of ResourceOptions from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        excluded_fields: Set[str] = set([])

        _dict = self.model_dump(
            by_alias=True,
            exclude=excluded_fields,
            exclude_none=True,
        )
        # set to None if memory (nullable) is None
        # and model_fields_set contains the field
        if self.memory is None and "memory" in self.model_fields_set:
            _dict["memory"] = None

        # set to None if cpu (nullable) is None
        # and model_fields_set contains the field
        if self.cpu is None and "cpu" in self.model_fields_set:
            _dict["cpu"] = None

        # set to None if gpu (nullable) is None
        # and model_fields_set contains the field
        if self.gpu is None and "gpu" in self.model_fields_set:
            _dict["gpu"] = None

        return _dict

    @classmethod
    def from_dict(cls, obj: Optional[Dict[str, Any]]) -> Optional[Self]:
        """Create an instance of ResourceOptions from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate(
            {"memory": obj.get("memory"), "cpu": obj.get("cpu"), "gpu": obj.get("gpu")}
        )
        return _obj

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
    SchedulingOptions
    """  # noqa: E501

    priority_class: Optional[StrictStr] = None
    queue_name: Optional[StrictStr] = None
    __properties: ClassVar[List[str]] = ["priority_class", "queue_name"]

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
    def from_json(cls, json_str: str) -> Optional[Self]:
        """Create an instance of SchedulingOptions from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        excluded_fields: Set[str] = set([])

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
    def from_dict(cls, obj: Optional[Dict[str, Any]]) -> Optional[Self]:
        """Create an instance of SchedulingOptions from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate(
            {
                "priority_class": obj.get("priority_class"),
                "queue_name": obj.get("queue_name"),
            }
        )
        return _obj


class JobOptions(BaseModel):
    """
    JobOptions
    """  # noqa: E501

    resources: Optional[ResourceOptions] = None
    image: Optional[ImageOptions] = None
    scheduling: Optional[SchedulingOptions] = None
    labels: Dict[str, StrictStr] = Field(default_factory=dict)
    __properties: ClassVar[List[str]] = ["resources", "image", "scheduling", "labels"]

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
    def from_json(cls, json_str: str) -> Optional[Self]:
        """Create an instance of JobOptions from a JSON string"""
        return cls.from_dict(json.loads(json_str))

    def to_dict(self) -> Dict[str, Any]:
        """Return the dictionary representation of the model using alias.

        This has the following differences from calling pydantic's
        `self.model_dump(by_alias=True)`:

        * `None` is only added to the output dict for nullable fields that
          were set at model initialization. Other fields with value `None`
          are ignored.
        """
        excluded_fields: Set[str] = set([])

        _dict = self.model_dump(
            by_alias=True,
            exclude=excluded_fields,
            exclude_none=True,
        )
        # override the default output from pydantic by calling `to_dict()` of resources
        if self.resources:
            _dict["resources"] = self.resources.to_dict()
        # override the default output from pydantic by calling `to_dict()` of image
        if self.image:
            _dict["image"] = self.image.to_dict()
        # override the default output from pydantic by calling `to_dict()` of scheduling
        if self.scheduling:
            _dict["scheduling"] = self.scheduling.to_dict()
        # set to None if resources (nullable) is None
        # and model_fields_set contains the field
        if self.resources is None and "resources" in self.model_fields_set:
            _dict["resources"] = None

        # set to None if image (nullable) is None
        # and model_fields_set contains the field
        if self.image is None and "image" in self.model_fields_set:
            _dict["image"] = None

        # set to None if scheduling (nullable) is None
        # and model_fields_set contains the field
        if self.scheduling is None and "scheduling" in self.model_fields_set:
            _dict["scheduling"] = None

        return _dict

    @classmethod
    def from_dict(cls, obj: Optional[Dict[str, Any]]) -> Optional[Self]:
        """Create an instance of JobOptions from a dict"""
        if obj is None:
            return None

        if not isinstance(obj, dict):
            return cls.model_validate(obj)

        _obj = cls.model_validate(
            {
                "resources": ResourceOptions.from_dict(obj["resources"])
                if obj.get("resources") is not None
                else None,
                "image": ImageOptions.from_dict(obj["image"])
                if obj.get("image") is not None
                else None,
                "scheduling": SchedulingOptions.from_dict(obj["scheduling"])
                if obj.get("scheduling") is not None
                else None,
                "labels": obj.get("labels"),
            }
        )
        return _obj


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
