import asyncio
import contextlib
import os
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path

from alphatrion.swarm.formats import Execution
from alphatrion.swarm.runtimes.base import Backend, Mount, Runtime, RuntimeSpec


class HostRuntime(Runtime):
    """
    A runtime on the host, without isolation, for development and tests.
    Its workspace is a temporary directory, and mounts are host directories
    used in place: guest paths under /work or a mount are mapped to host
    paths in cwd, file paths and command arguments. Each command runs in a
    process group of its own, so stopping the runtime ends every process it
    started, the children of commands included. python is the interpreter
    running the engine.
    """

    def __init__(self, root: Path, spec: RuntimeSpec, mounts: list[Mount]):
        self._root = root
        # Longest guest paths first, so a nested mount wins.
        self._paths = sorted(
            [(self.WORKDIR, root), *((m.guest, Path(m.host)) for m in mounts)],
            key=lambda p: len(p[0]),
            reverse=True,
        )
        self._env = {
            **os.environ,
            "PATH": f"{Path(sys.executable).parent}{os.pathsep}{os.environ.get('PATH', '')}",
            **spec.env,
        }
        self._processes: set[asyncio.subprocess.Process] = set()

    def host(self, path: str) -> str:
        """The host path of a guest path, the path itself if it isn't under
        /work or a mount."""
        for guest, host in self._paths:
            if path == guest or path.startswith(guest.rstrip("/") + "/"):
                return str(host / os.path.relpath(path, guest))
        return path

    async def exec(
        self,
        command: str,
        args: list[str] | None = None,
        cwd: str | None = None,
        env: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> Execution:
        start = time.monotonic()
        process = await asyncio.create_subprocess_exec(
            command,
            *(self.host(a) for a in args or []),
            cwd=self.host(cwd or self.WORKDIR),
            env={**self._env, **(env or {})},
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            start_new_session=True,
        )
        self._processes.add(process)
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
        except TimeoutError:
            await _end(process, grace=0)
            self._processes.discard(process)
            return Execution(
                exit_code=None, duration=time.monotonic() - start, timed_out=True
            )
        # Cancelled, e.g. when the node timed out, the process stays tracked,
        # so stopping the runtime ends it.
        self._processes.discard(process)
        return Execution(
            exit_code=process.returncode,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
            duration=time.monotonic() - start,
        )

    async def write(self, path: str, content: str | bytes) -> None:
        file = Path(self.host(path))
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(content.encode() if isinstance(content, str) else content)

    async def read(self, path: str) -> bytes:
        return Path(self.host(path)).read_bytes()

    async def stop(self, timeout: float) -> None:
        await asyncio.gather(*(_end(p, grace=timeout) for p in self._processes))
        self._processes.clear()

    async def kill(self) -> None:
        await asyncio.gather(*(_end(p, grace=0) for p in self._processes))
        self._processes.clear()

    async def remove(self) -> None:
        shutil.rmtree(self._root, ignore_errors=True)


async def _end(process: asyncio.subprocess.Process, grace: float) -> None:
    """End a process and its children: terminate its group, and kill it if
    it hasn't ended after grace seconds."""
    if process.returncode is not None:
        return
    with contextlib.suppress(ProcessLookupError):
        os.killpg(process.pid, signal.SIGTERM if grace > 0 else signal.SIGKILL)
    try:
        await asyncio.wait_for(process.wait(), grace or None)
    except TimeoutError:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        await process.wait()


class HostBackend(Backend):
    """Runs runtimes on the host, without isolation: for development and
    tests, not for code a model wrote."""

    type = "host"
    isolated = False

    async def create(
        self,
        name: str,
        spec: RuntimeSpec,
        mounts: list[Mount],
        max_duration: float | None,
    ) -> Runtime:
        root = Path(tempfile.mkdtemp(prefix=f"{name}-"))
        return HostRuntime(root, spec, mounts)
