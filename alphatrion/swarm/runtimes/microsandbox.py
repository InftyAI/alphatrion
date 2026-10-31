"""
Runtimes in microVMs, with https://github.com/superradcompany/microsandbox:
hardware-isolated, started as child processes of the engine with no daemon,
or on microsandbox's cloud, which the SDK picks from its environment, e.g.
MSB_BACKEND=cloud with MSB_API_KEY. Install it with `pip install
microsandbox`. It is beta software, so every call to it is in this module.

Mounts bind directories of this machine, so they work on local microVMs
only; on the cloud they would need copying in, which isn't done yet.
"""

import time
from typing import Any

from alphatrion.swarm.formats import Execution
from alphatrion.swarm.runtimes.base import Backend, Mount, Runtime, RuntimeSpec


def _sdk() -> Any:
    try:
        import microsandbox
    except ImportError:
        raise RuntimeError(
            "The microsandbox backend needs `pip install microsandbox`"
        ) from None
    return microsandbox


class MicrosandboxRuntime(Runtime):
    def __init__(self, sandbox: Any, name: str):
        self._sandbox = sandbox
        self._name = name

    async def exec(
        self,
        command: str,
        args: list[str] | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> Execution:
        start = time.monotonic()
        try:
            output = await self._sandbox.exec(
                command, args or [], cwd=cwd or self.WORKDIR, env=env, timeout=timeout
            )
        except _sdk().ExecTimeoutError:
            return Execution(
                exit_code=None, duration=time.monotonic() - start, timed_out=True
            )
        return Execution(
            exit_code=output.exit_code,
            stdout=output.stdout_text,
            stderr=output.stderr_text,
            duration=time.monotonic() - start,
        )

    async def write(self, path: str, content: str | bytes) -> None:
        data = content.encode() if isinstance(content, str) else content
        await self._sandbox.fs.write(path, data)

    async def read(self, path: str) -> bytes:
        return await self._sandbox.fs.read(path)

    async def stop(self, timeout: float) -> None:
        await self._sandbox.stop(timeout=timeout)

    async def kill(self) -> None:
        await self._sandbox.kill()

    async def remove(self) -> None:
        await _sdk().Sandbox.remove(self._name)


class MicrosandboxBackend(Backend):
    type = "microsandbox"

    async def create(
        self,
        name: str,
        spec: RuntimeSpec,
        mounts: list[Mount],
        max_duration: float | None,
    ) -> Runtime:
        sdk = _sdk()
        sandbox = await sdk.Sandbox.create(
            name,
            image=spec.image,
            cpus=spec.cpus,
            memory=spec.memory,
            workdir=Runtime.WORKDIR,
            env=spec.env or None,
            volumes={
                m.guest: sdk.Volume.bind(m.host, readonly=m.readonly) for m in mounts
            }
            or None,
            # The microVM ends itself at this deadline, even if the engine's
            # process dies.
            max_duration=max_duration,
            replace=True,
        )
        return MicrosandboxRuntime(sandbox, name)
