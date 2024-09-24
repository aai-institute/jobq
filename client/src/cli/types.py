import logging

from pydantic import AnyHttpUrl, Field, ValidationInfo, field_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    PyprojectTomlConfigSettingsSource,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    api_base_url: AnyHttpUrl = Field(
        description="Base URL of the jobq API server",
        validation_alias="api-base-url",
    )
    log_level: str = Field(
        "INFO",
        description="Output log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        validation_alias="log-level",
    )

    @field_validator("log_level", mode="before")
    @classmethod
    def log_level_validator(cls, v: str, info: ValidationInfo) -> str:
        if v not in logging._nameToLevel.keys():
            raise ValueError(f"invalid log level name {v!r}")
        return v

    model_config = SettingsConfigDict(
        extra="ignore",
        env_prefix="JOBQ_",
        pyproject_toml_table_header=("tool", "jobq"),
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            env_settings,
            PyprojectTomlConfigSettingsSource(settings_cls),
        )
