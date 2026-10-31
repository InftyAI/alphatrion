from alphatrion.swarm.runtimes.base import (
    Backend,
    Mount,
    MountSpec,
    Runtime,
    RuntimePlan,
    RuntimeSpec,
)
from alphatrion.swarm.runtimes.host import HostBackend, HostRuntime
from alphatrion.swarm.runtimes.microsandbox import (
    MicrosandboxBackend,
    MicrosandboxRuntime,
)

# The built-in backends, by type.
BUILTIN_BACKENDS: dict[str, Backend] = {
    backend.type: backend for backend in (HostBackend(), MicrosandboxBackend())
}

__all__ = [
    "BUILTIN_BACKENDS",
    "Backend",
    "HostBackend",
    "HostRuntime",
    "MicrosandboxBackend",
    "MicrosandboxRuntime",
    "Mount",
    "MountSpec",
    "Runtime",
    "RuntimePlan",
    "RuntimeSpec",
]
