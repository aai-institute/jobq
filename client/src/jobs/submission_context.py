import logging
import platform
import subprocess
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from typing import Any, TypeVar, overload

T = TypeVar("T")
TDefault = TypeVar("TDefault")


@overload
def _maybe(fn: Callable[..., T]) -> T | None: ...


@overload
def _maybe(fn: Callable[..., T], default_value: TDefault) -> T | TDefault: ...


def _maybe(
    fn: Callable[..., T], default_value: TDefault | None = None
) -> T | TDefault | None:
    try:
        return fn()
    except:  # noqa E722
        logging.debug(
            f"Failed to execute {fn.__name__}, using fallback {default_value}"
        )
        return default_value


def get_git_config_info(item: str) -> str:
    return _maybe(
        lambda: subprocess.check_output(
            ["git", "config", item], encoding="utf-8"
        ).strip(),
        "Unknown",
    )


def get_git_username() -> str:
    return get_git_config_info("user.name")


def get_git_user_email() -> str:
    return get_git_config_info("user.email")


def determine_platform_info() -> dict[str, Any]:
    skip = ["system_alias"]
    return {
        name: _maybe(fn)
        for name, fn in platform.__dict__.items()
        if callable(fn) and not name.startswith("_") and name not in skip
    }


@dataclass
class SubmitterInformation:
    username: str = field(default_factory=lambda: get_git_config_info("user.name"))
    email: str = field(default_factory=lambda: get_git_config_info("user.email"))


@dataclass
class SubmissionContext:
    submitter: SubmitterInformation = field(default_factory=SubmitterInformation)
    platform_info: dict[str, Any] = field(default_factory=determine_platform_info)

    def to_dict(self) -> dict[str, Any]:
        return {
            "submitter": asdict(self.submitter),
            "platform": self.platform_info,
        }
