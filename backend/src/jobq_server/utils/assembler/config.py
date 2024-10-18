from __future__ import annotations

import re
from dataclasses import field
from io import IOBase
from pathlib import Path
from typing import Annotated

import yaml
from annotated_types import Interval
from jobq.types import AnyPath
from pydantic import BaseModel, Field, field_validator, model_validator
from typing_extensions import TypeAliasType


class DependencySpec(BaseModel):
    apt: list[str]
    pip: list[str]


def validate_env_mapping(val: list[str]) -> list[str]:
    def _validate_entry(val: str) -> str:
        parts = val.split("=")

        if len(parts) != 2:
            raise ValueError(
                "Environment variable mapping must be in the form 'KEY=VALUE'"
            )

        key, value = parts

        if not key:
            raise ValueError("Environment variable key cannot be empty")
        if not value:
            raise ValueError("Environment variable value cannot be empty")

        # Validate key format to ensure it is a valid shell environment variable name
        key_pattern = r"^[a-zA-Z_][a-zA-Z0-9_]*$"
        if not re.match(key_pattern, key):
            raise ValueError(
                "Environment variable key must be a valid shell environment variable name"
            )

        return val

    return [_validate_entry(v) for v in val]


class FilesystemSpec(BaseModel):
    # (m.mynter) copy shadows depricated method in BaseModel but we use it to stay with docker nomenclature
    copy: dict[str, str] = Field(default_factory=dict)  # type: ignore[assignment]
    add: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="before")
    def preprocess_copy_add(cls, values):
        for model_field in ["copy", "add"]:
            if model_field in values and isinstance(values[model_field], list):
                instruct_dict = {}
                for instruct in values[model_field]:
                    parts = instruct.split(":")
                    if len(parts) != 2:
                        raise ValueError(
                            "Filesystem operation must be in the form 'SOURCE:TARGET'"
                        )
                    src, tgt = parts
                    instruct_dict[src.strip()] = tgt.strip()
                values[model_field] = instruct_dict
        return values


class ConfigSpec(BaseModel):
    env: list[str] = Field(default_factory=list)
    arg: list[str] = Field(default_factory=list)
    stopsignal: Annotated[int, Interval(ge=1, le=31)] | str | None = None
    shell: str | None = None

    @model_validator(mode="before")
    @classmethod
    def preprocess_env_arg(cls, values):
        for model_field in ["env", "arg"]:
            if model_field in values and isinstance(values[model_field], dict):
                values[model_field] = [
                    f"{k}={v}" for k, v in values[model_field].items()
                ]
        return values

    _validate_env = field_validator("env")(validate_env_mapping)
    _validate_arg = field_validator("arg")(validate_env_mapping)


class MetaSpec(BaseModel):
    labels: list[str] = field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def coerce_kv_string(cls, val):
        if isinstance(val["labels"], dict):
            val["labels"] = [f"{k}={v}" for k, v in val["labels"].items()]
        return val

    @field_validator("labels")
    def _validate_labels(cls, val):
        for label in val:
            parts = label.split("=")
            if len(parts) != 2:
                raise ValueError("Label must be in the form 'KEY=VALUE'")

            key, value = parts
            if not key:
                raise ValueError("Label key cannot be empty")
            if not value:
                raise ValueError("Label value cannot be empty")

        return val


Identifier = TypeAliasType("Identifier", Annotated[int, Interval(ge=0, le=65535)])
"""UID/GID identifier type"""


class UserSpec(BaseModel):
    name: str = ""
    uid: Identifier | None = None
    gid: Identifier | None = None
    create: bool = True


class BuildSpec(BaseModel):
    base_image: str
    dependencies: DependencySpec | None = None
    user: UserSpec | None = None
    config: ConfigSpec | None = None
    meta: MetaSpec | None = None
    filesystem: FilesystemSpec | None = None
    workdir: str | None = None
    volumes: list[str] | None = None


class Config(BaseModel):
    build: BuildSpec


def load_config(config_source: AnyPath | IOBase) -> Config:
    # If config_source is a file object, directly read the YAML content from it
    if isinstance(config_source, IOBase):
        config_yaml = yaml.safe_load(config_source)
    else:
        with Path(config_source).open() as f:
            config_yaml = yaml.safe_load(f)

    return Config(**config_yaml)
