import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass(slots=True)
class DependencySpec:
    apt: list[str]
    pip: list[str]


@dataclass(slots=True)
class VolumeSpec:
    host_path: str
    container_path: str


@dataclass(slots=True)
class FilesystemSpec:
    workdir: str | None = None
    copy: list[dict[str, str]] = field(default_factory=list)
    add: list[dict[str, str]] = field(default_factory=list)


@dataclass(slots=True)
class ConfigSpec:
    env: list[dict[str, str]] = field(default_factory=list)
    arg: list[dict[str, str]] = field(default_factory=list)
    stopsignal: str | None = None
    shell: str | None = None


@dataclass(slots=True)
class MetaSpec:
    labels: list[dict[str, str]]


@dataclass(slots=True)
class UserSpec:
    name: str


@dataclass(slots=True)
class BuildSpec:
    base_image: str
    dependencies: DependencySpec | None = None
    user: UserSpec | None = None
    config: ConfigSpec | None = None
    meta: MetaSpec | None = None
    filesystem: FilesystemSpec | None = None
    volumes: list[VolumeSpec] | None = None

    def __post_init__(self):
        def _coerce_spec(val, spec):
            return spec(**val) if isinstance(val, dict) else val

        self.dependencies = _coerce_spec(self.dependencies, DependencySpec)
        self.volumes = (
            [_coerce_spec(v, VolumeSpec) for v in self.volumes]
            if self.volumes
            else None
        )
        self.user = _coerce_spec(self.user, UserSpec)
        self.config = _coerce_spec(self.config, ConfigSpec)
        self.meta = _coerce_spec(self.meta, MetaSpec)
        self.filesystem = _coerce_spec(self.filesystem, FilesystemSpec)


@dataclass(slots=True)
class Config:
    build: BuildSpec

    def __post_init__(self):
        self.build = BuildSpec(**self.build)


def load_config(config_path: os.PathLike[str]) -> Config:
    with Path(config_path).open() as f:
        config_yaml = yaml.safe_load(f)
    return Config(**config_yaml)
