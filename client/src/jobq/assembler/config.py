from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from jobq.types import AnyPath


@dataclass(frozen=True, slots=True)
class DependencySpec:
    apt: list[str]
    pip: list[str]


@dataclass(frozen=True, slots=True)
class VolumeSpec:
    host_path: str
    container_path: str


@dataclass(frozen=True, slots=True)
class FilesystemSpec:
    copy: list[dict[str, str]] = field(default_factory=list)
    add: list[dict[str, str]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ConfigSpec:
    env: list[dict[str, str]] = field(default_factory=list)
    arg: list[dict[str, str]] = field(default_factory=list)
    stopsignal: str | None = None
    shell: str | None = None


@dataclass(frozen=True, slots=True)
class MetaSpec:
    labels: list[dict[str, str]]


@dataclass(frozen=True, slots=True)
class UserSpec:
    name: str = ""
    uid: int | None = None
    gid: int | None = None
    create: bool = True


@dataclass(frozen=True, slots=True)
class BuildSpec:
    base_image: str
    dependencies: DependencySpec | None = None
    user: UserSpec | None = None
    config: ConfigSpec | None = None
    meta: MetaSpec | None = None
    filesystem: FilesystemSpec | None = None
    workdir: str | None = None
    volumes: list[VolumeSpec] | None = None

    def __post_init__(self):
        specs = {
            "dependencies": DependencySpec,
            "user": UserSpec,
            "config": ConfigSpec,
            "meta": MetaSpec,
            "filesystem": FilesystemSpec,
            "volumes": VolumeSpec,
        }

        def _coerce_spec(val, spec):
            return spec(**val) if isinstance(val, dict) else val

        for attr, spec in specs.items():
            orig_value = getattr(self, attr)
            if attr == "volumes" and orig_value is not None:
                coerced_value = [_coerce_spec(v, spec) for v in orig_value]
            else:
                coerced_value = _coerce_spec(orig_value, spec)
            object.__setattr__(self, attr, coerced_value)


@dataclass(frozen=True, slots=True)
class Config:
    build: BuildSpec

    def __post_init__(self):
        if isinstance(self.build, dict):
            object.__setattr__(self, "build", BuildSpec(**self.build))


def load_config(config_path: AnyPath) -> Config:
    with Path(config_path).open() as f:
        config_yaml = yaml.safe_load(f)
    return Config(**config_yaml)
