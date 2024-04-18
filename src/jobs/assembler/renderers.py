import textwrap
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable

from typing_extensions import override

from jobs.assembler import Config


class Renderer(ABC):
    def __init__(self, config: Config) -> None:
        self.config = config

    @classmethod
    def _check_attribute(cls, attr_path, config) -> bool:
        attributes = attr_path.split(".")
        current_level = config
        for attr in attributes:
            current_level = getattr(current_level, attr, None)
            if current_level is None:
                return False
        return True

    @classmethod
    def _render_items(
        cls, render_func: Callable[[str, str], str], container: list[dict[str, str]]
    ) -> list[str]:
        return [
            render_func(key, val) for item in container for key, val in item.items()
        ]

    @classmethod
    @abstractmethod
    def accepts(cls, config: Config) -> bool: ...

    @abstractmethod
    def render(self) -> str: ...


class BaseImageRenderer(Renderer):
    @classmethod
    @override
    def accepts(cls, config: Config) -> bool:
        return cls._check_attribute("build.base_image", config)

    @override
    def render(self) -> str:
        output = f"FROM {self.config.build.base_image}\n"
        if self.config.build.workdir:
            output += f"WORKDIR {self.config.build.workdir}"
        return output


class AptDependencyRenderer(Renderer):
    @classmethod
    @override
    def accepts(cls, config: Config) -> bool:
        return cls._check_attribute("build.dependencies.apt", config)

    @override
    def render(self) -> str:
        packages = self.config.build.dependencies.apt

        # Buildkit caches to improve performance during rebuilds
        run_options = [
            "--mount=type=cache,target=/var/lib/apt/lists,sharing=locked",
            "--mount=type=cache,target=/var/cache/apt,sharing=locked",
        ]

        return textwrap.dedent(
            f"""
            RUN {' '.join(run_options)} \\
            rm -f /etc/apt/apt.conf.d/docker-clean && \\
            apt-get update && \\
            apt-get install -y --no-install-recommends {' '.join(packages)}
            """
        ).strip()


class PythonDependencyRenderer(Renderer):
    @classmethod
    @override
    def accepts(cls, config: Config) -> bool:
        return cls._check_attribute("build.dependencies.pip", config)

    @override
    def render(self) -> str:
        result = ""

        packages = self.config.build.dependencies.pip

        # Buildkit cache to improve performance during rebuilds
        run_options = ["--mount=type=cache,target=/root/.cache/pip,sharing=locked"]

        # Copy any requirements.txt files to the image
        reqs_files = [
            p.split()[1] for p in packages if p.startswith(("-r", "--requirement"))
        ]
        if reqs_files:
            result += f"COPY {' '.join(reqs_files)} .\n"

        # ... and install those before and local projects
        result += f"RUN {' '.join(run_options)} pip install {' '.join(f'-r {r}' for r in reqs_files)}\n"

        # Next install local projects (built wheels or editable installs)
        build_folders = [
            str(folder)
            for p in packages
            if (folder := Path(p)).is_dir() and (folder / "pyproject.toml").is_file()
        ]
        if build_folders:
            result += f"COPY {' '.join(build_folders)} .\n"

        editable_installs = [
            p.split()[1] for p in packages if p.startswith(("-e", "--editable"))
        ]
        for root_dir in editable_installs:
            pyproject_toml = Path(root_dir) / "pyproject.toml"
            if not pyproject_toml.exists():
                continue
            result += f"COPY {root_dir} .\n"

        result += f"RUN {' '.join(run_options)} pip install {' '.join(set(build_folders) | set(editable_installs))}\n"

        return result


class UserRenderer(Renderer):
    @classmethod
    @override
    def accepts(cls, config: Config) -> bool:
        return cls._check_attribute("build.user", config)

    @override
    def render(self) -> str:
        # TODO: check for a safe way that works on all images and takes care of where to use adduser, useradd and what creation arguments to add.
        username = self.config.build.user.name
        return textwrap.dedent(
            f"""
        RUN useradd -m {username}
        USER {username}
        """
        ).strip()


class MetaRenderer(Renderer):
    @classmethod
    @override
    def accepts(cls, config: Config) -> bool:
        return cls._check_attribute("build.meta", config)

    @override
    def render(self) -> str:
        labels = self.config.build.meta.labels

        return textwrap.dedent(
            "LABEL "
            + " ".join(self._render_items(lambda key, val: f"{key}={val}", labels))
        ).strip()


class ConfigRenderer(Renderer):
    @classmethod
    @override
    def accepts(cls, config: Config) -> bool:
        return cls._check_attribute("build.config", config)

    @override
    def render(self) -> str:
        if not self.config.build.config:
            return ""
        envs = self.config.build.config.env or []
        args = self.config.build.config.arg or []
        shell = self.config.build.config.shell
        stopsignal = self.config.build.config.stopsignal

        env_lines = "\n".join(
            self._render_items(lambda key, val: f"ENV {key}={val}", envs)
        )

        arg_lines = "\n".join(
            self._render_items(lambda key, val: f"ARG {key}={val}", args)
        )

        shell_line = f'SHELL ["/bin/{shell}", "-c"]' if shell else "\n"
        stopsignal_line = f"STOPSIGNAL {stopsignal}" if stopsignal else "\n"
        return textwrap.dedent(
            f"""
        {env_lines}
        {arg_lines}
        {shell_line}
        {stopsignal_line}
        """
        ).strip()


class FileSystemRenderer(Renderer):
    @classmethod
    @override
    def accepts(cls, config: Config) -> bool:
        return cls._check_attribute("build.filesystem", config)

    @override
    def render(self) -> str:
        if not self.config.build.filesystem:
            return ""
        copy = self.config.build.filesystem.copy
        add = self.config.build.filesystem.add

        copy_lines = "\n".join(
            self._render_items(lambda key, val: f"COPY {key} {val}", copy)
        )

        add_lines = "\n".join(
            self._render_items(lambda key, val: f"ADD {key} {val}", add)
        )

        return textwrap.dedent(
            f"""
        {copy_lines}
        {add_lines}
        """
        ).strip()


RENDERERS = [
    BaseImageRenderer,
    MetaRenderer,
    ConfigRenderer,
    AptDependencyRenderer,
    PythonDependencyRenderer,
    FileSystemRenderer,
    UserRenderer,
]
