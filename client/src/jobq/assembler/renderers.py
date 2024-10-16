import io
import operator
import textwrap
from abc import ABC, abstractmethod
from pathlib import Path
from typing import cast

from typing_extensions import override

from jobq.assembler import Config
from jobq.assembler.config import DependencySpec, MetaSpec, UserSpec


class Renderer(ABC):
    def __init__(self, config: Config) -> None:
        self.config = config

    @classmethod
    def _check_attribute(cls, attr_path: str, config: object) -> bool:
        try:
            _ = operator.attrgetter(attr_path)(config)
            return True
        except AttributeError:
            return False

    @classmethod
    @abstractmethod
    def accepts(cls, config: Config) -> bool: ...

    @abstractmethod
    def render(self) -> str: ...


class BaseImageRenderer(Renderer):
    _base_image_path: str = "build.base_image"

    @classmethod
    @override
    def accepts(cls, config: Config) -> bool:
        return cls._check_attribute(cls._base_image_path, config)

    @override
    def render(self) -> str:
        output = f"FROM {self.config.build.base_image}\n"
        return output


class AptDependencyRenderer(Renderer):
    _apt_dependency_path = "build.dependencies.apt"

    @classmethod
    @override
    def accepts(cls, config: Config) -> bool:
        return cls._check_attribute(cls._apt_dependency_path, config)

    @override
    def render(self) -> str:
        packages = cast(DependencySpec, self.config.build.dependencies).apt
        if not packages:
            return ""

        # Buildkit caches to improve performance during rebuilds
        run_options = [
            "--mount=type=cache,target=/var/lib/apt/lists,sharing=shared",
            "--mount=type=cache,target=/var/cache/apt,sharing=shared",
        ]

        return textwrap.dedent(
            f"""
            RUN {" ".join(run_options)} \\
            rm -f /etc/apt/apt.conf.d/docker-clean && \\
            apt-get update && \\
            apt-get install -y --no-install-recommends {" ".join(packages)}
            """
        ).strip()


class PythonDependencyRenderer(Renderer):
    _pip_dependency_path: str = "build.dependencies.pip"

    @classmethod
    @override
    def accepts(cls, config: Config) -> bool:
        return cls._check_attribute(cls._pip_dependency_path, config)

    @override
    def render(self) -> str:
        result = ""

        # List will be modified, so make a copy
        packages = cast(DependencySpec, self.config.build.dependencies).pip.copy()
        user_opts = self.config.build.user

        copy_options = []
        if user_opts:
            if user_opts.name:
                copy_options.append(f"--chown={user_opts.name}")
            else:
                if user_opts.gid is not None:
                    copy_options.append(f"--chown={user_opts.uid}:{user_opts.gid}")
                else:
                    copy_options.append(f"--chown={user_opts.uid}")

        # Buildkit cache to improve performance during rebuilds
        run_options = ["--mount=type=cache,target=~/.cache/pip,sharing=shared"]

        # Copy any direct Wheel dependencies to the image
        wheels = [p for p in packages if p.endswith(".whl")]
        map(packages.remove, wheels)
        if wheels:
            result += f"COPY {' '.join(copy_options)} {' '.join(wheels)} .\n"

        # Copy any requirements.txt files to the image
        reqs_packages = [p for p in packages if p.startswith(("-r", "--requirement"))]
        reqs_files = [p.split()[1] for p in reqs_packages]
        map(packages.remove, reqs_packages)
        if reqs_files:
            result += f"COPY {' '.join(copy_options)} {' '.join(reqs_files)} .\n"
            # ... and install those before and local projects
            result += f"RUN {' '.join(run_options)} pip install {' '.join(f'-r {r}' for r in reqs_files)}\n"

        # Next install local projects (built wheels or editable installs)
        build_packages = [
            p
            for p in packages
            if (folder := Path(p)).is_dir() and (folder / "pyproject.toml").is_file()
        ]
        build_folders = [str(folder) for p in build_packages]
        map(packages.remove, build_packages)
        if build_folders:
            result += f"COPY {' '.join(copy_options)} {' '.join(build_folders)} .\n"

        editable_packages = [
            p for p in packages if p.startswith(("-r", "--requirement"))
        ]
        editable_installs = [p.split()[1] for p in editable_packages]
        map(packages.remove, editable_packages)
        for root_dir in editable_installs:
            pyproject_toml = Path(root_dir) / "pyproject.toml"
            if not pyproject_toml.exists():
                continue
            result += f"COPY {' '.join(copy_options)} {root_dir} .\n"

        local_packages = set(build_folders) | set(editable_installs)
        if local_packages:
            result += (
                f"RUN {' '.join(run_options)} pip install {' '.join(local_packages)}\n"
            )

        # Finally install any remaining packages (which should be regular packages)
        if packages:
            result += f"RUN {' '.join(run_options)} pip install {' '.join(packages)}\n"

        return result


class UserRenderer(Renderer):
    _user_path: str = "build.user"

    @classmethod
    @override
    def accepts(cls, config: Config) -> bool:
        return cls._check_attribute(cls._user_path, config)

    @override
    def render(self) -> str:
        # TODO: check for a safe way that works on all images and takes care of where to use adduser, useradd and what creation arguments to add.
        opts = cast(UserSpec, self.config.build.user)
        result = io.StringIO()

        if opts.name:
            if opts.create:
                useradd_args = [f"-m {opts.name}"]
                if opts.uid is not None:
                    useradd_args.append(f"-u {opts.uid}")
                if opts.gid is not None:
                    useradd_args.append(f"-g {opts.gid}")
                result.write(f"RUN useradd {' '.join(useradd_args)}\n")
            result.write(f"USER {opts.name}")
        else:
            result.write(f"USER {opts.uid}")
            if opts.gid is not None:
                result.write(f":{opts.gid}")

        result.write("\n")

        if self.config.build.workdir:
            result.write(f"WORKDIR {self.config.build.workdir}\n")

        result.write("ENV PATH=$HOME/.local/bin:$PATH\n")

        return result.getvalue().strip()


class MetaRenderer(Renderer):
    _meta_path: str = "build.meta.labels"

    @classmethod
    @override
    def accepts(cls, config: Config) -> bool:
        return cls._check_attribute(cls._meta_path, config)

    @override
    def render(self) -> str:
        labels = cast(MetaSpec, self.config.build.meta).labels
        return textwrap.dedent("LABEL " + " ".join(labels)).strip()


class ConfigRenderer(Renderer):
    _config_path: str = "build.config"
    _default_envs = ["PYTHONUNBUFFERED=1"]  # Enable unbuffered stdout/stderr by default

    @classmethod
    @override
    def accepts(cls, config: Config) -> bool:
        return cls._check_attribute(cls._config_path, config)

    @override
    def render(self) -> str:
        if not self.config.build.config:
            return ""
        envs = self._default_envs + (self.config.build.config.env or [])
        args = self.config.build.config.arg or []
        shell = self.config.build.config.shell
        stopsignal = self.config.build.config.stopsignal

        env_lines = "\n".join(f"ENV {env}" for env in envs)
        arg_lines = "\n".join(f"ARG {arg}" for arg in args)

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


class VolumesRenderer(Renderer):
    _volumes_path: str = "build.volumes"

    @classmethod
    @override
    def accepts(cls, config: Config) -> bool:
        return cls._check_attribute(cls._volumes_path, config)

    @override
    def render(self) -> str:
        if not self.config.build.volumes:
            return ""
        volumes = ['"' + v + '"' for v in self.config.build.volumes]
        return f"VOLUME {volumes}"


class FileSystemRenderer(Renderer):
    _filesystem_path: str = "build.filesystem"

    @classmethod
    @override
    def accepts(cls, config: Config) -> bool:
        return cls._check_attribute(cls._filesystem_path, config)

    @override
    def render(self) -> str:
        if not self.config.build.filesystem:
            return ""
        copy = self.config.build.filesystem.copy
        add = self.config.build.filesystem.add

        opts = []
        user_opts = self.config.build.user
        if user_opts:
            if user_opts.name:
                opts.append(f"--chown={user_opts.name}")
            else:
                if user_opts.gid is not None:
                    opts.append(f"--chown={user_opts.uid}:{user_opts.gid}")
                else:
                    opts.append(f"--chown={user_opts.uid}")

        copy_lines = "\n".join([
            f"COPY {' '.join(opts)} {k} {v}" for k, v in copy.items()
        ])

        add_lines = "\n".join([f"ADD {' '.join(opts)} {k} {v}" for k, v in add.items()])

        return textwrap.dedent(
            f"""
        {copy_lines}
        {add_lines}
        """
        ).strip()


RENDERERS: list[type[Renderer]] = [
    BaseImageRenderer,
    MetaRenderer,
    ConfigRenderer,
    AptDependencyRenderer,
    UserRenderer,
    VolumesRenderer,
    PythonDependencyRenderer,
    FileSystemRenderer,
]
