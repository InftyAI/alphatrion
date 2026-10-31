from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field, model_validator

from alphatrion.swarm.formats import Execution


class MountSpec(BaseModel):
    """A directory mounted in a runtime. Its source is like a node param: a
    host directory relative to the pipeline file, ${inputs.name} for a
    directory the run is given, or ${params.name} for a setting of the
    pipeline."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="Where it is in the runtime, e.g. /data.")
    source: str = Field(
        description="The host directory: a path relative to the pipeline file, "
        "${inputs.name} or ${params.name}."
    )
    readonly: bool = True

    @model_validator(mode="after")
    def absolute_path(self) -> "MountSpec":
        if not self.path.startswith("/"):
            raise ValueError(f"Mount path {self.path!r} must be absolute")
        return self


class RuntimeSpec(BaseModel):
    """
    A runtime the nodes referencing it by name run in, defined in the
    pipeline's runtimes section, so it is part of the fixed root: nodes
    choose a runtime, but never change what it allows.
    """

    model_config = ConfigDict(extra="forbid")

    type: str = Field(
        description="The backend creating it, e.g. host, microsandbox or kubernetes."
    )
    image: str | None = Field(default=None, description="The image, e.g. python.")
    cpus: int | None = Field(default=None, ge=1)
    memory: int | None = Field(default=None, ge=1, description="In MiB.")
    env: dict[str, str] = Field(default_factory=dict)
    mounts: list[MountSpec] = Field(
        default_factory=list,
        description="Directories mounted in the runtime, read-only unless "
        "readonly is false, e.g. {path: /data, source: ${inputs.data}} for a "
        "directory the run is given, or {path: /code, source: code} for one "
        "relative to the pipeline file.",
    )

    @model_validator(mode="after")
    def unique_paths(self) -> "RuntimeSpec":
        paths = [m.path for m in self.mounts]
        repeated = sorted({p for p in paths if paths.count(p) > 1})
        if repeated:
            raise ValueError(f"Mounts repeat paths: {', '.join(repeated)}")
        return self


class Mount(BaseModel):
    """A resolved mount: a host directory at a guest path."""

    host: str
    guest: str
    readonly: bool = True


class Runtime(ABC):
    """
    Where a node runs code, e.g. a microVM or a Kubernetes pod. Its
    workspace is /work, where files are written and commands run by
    default. The engine creates one for each attempt of a node that has a
    runtime, and stops it when the attempt ends, so a timeout ends
    everything running in it.
    """

    WORKDIR: ClassVar[str] = "/work"

    @abstractmethod
    async def exec(
        self,
        command: str,
        args: list[str] | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> Execution:
        """Run a command, e.g. exec("python", ["train.py"]). A command
        running longer than timeout seconds is killed, and the execution is
        timed out."""

    @abstractmethod
    async def write(self, path: str, content: str | bytes) -> None: ...

    @abstractmethod
    async def read(self, path: str) -> bytes: ...

    @abstractmethod
    async def stop(self, timeout: float) -> None:
        """Stop gracefully, waiting up to timeout seconds."""

    @abstractmethod
    async def kill(self) -> None:
        """Stop at once, whatever is running."""

    @abstractmethod
    async def remove(self) -> None:
        """Remove what the runtime left, once stopped."""


class Backend(ABC):
    """Creates runtimes of a type, e.g. microVMs or Kubernetes pods. Custom
    backends subclass it and are passed to build_graph(backends=[...])."""

    type: ClassVar[str]
    # Whether its runtimes isolate the code they run from the host.
    isolated: ClassVar[bool] = True

    @abstractmethod
    async def create(
        self,
        name: str,
        spec: RuntimeSpec,
        mounts: list[Mount],
        max_duration: float | None,
    ) -> Runtime:
        """Create and start a runtime. max_duration, if set, is a deadline
        the backend enforces itself, so a runtime never outlives it even if
        the engine's process dies."""


class RuntimePlan:
    """A node's runtime, resolved when the pipeline is built: its backend,
    its spec, and its mounts, whose sources are host paths or, for inputs of
    the run, only known when a run starts."""

    def __init__(
        self,
        backend: Backend,
        spec: RuntimeSpec,
        mounts: list[tuple[MountSpec, str | None]],
    ):
        """mounts pair each mount, with its source resolved to a host path,
        with the input it comes from, if any."""
        self.backend = backend
        self.spec = spec
        self._mounts = mounts

    def mounts(self, inputs: dict) -> list[Mount]:
        return [
            Mount(
                host=str(inputs[name] if name is not None else m.source),
                guest=m.path,
                readonly=m.readonly,
            )
            for m, name in self._mounts
        ]
