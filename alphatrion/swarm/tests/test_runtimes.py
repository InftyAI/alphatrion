import asyncio
import os
import sys
import types
from pathlib import Path

import pytest
import yaml

from alphatrion.swarm import GraphStatus, Pipeline, build_graph, check_mutation
from alphatrion.swarm.runtimes import MicrosandboxBackend, Mount, RuntimeSpec


def build(pipeline: str, functions: dict, base_dir: Path | None = None):
    return build_graph(yaml.safe_load(pipeline), functions=functions)


# Timeouts and retries.


@pytest.mark.asyncio
async def test_a_node_past_its_timeout_takes_the_timeout_choice():
    async def slow(state):
        await asyncio.sleep(10)

    graph = build(
        """
        nodes:
          - name: slow
            type: action
            fn: slow
            timeout: 0.1
            branches: {timeout: [{name: after, type: action, fn: after}]}
        """,
        {"slow": slow, "after": lambda state: "recovered"},
    )
    result = await graph.run()
    assert result.status == GraphStatus.COMPLETED, result.error
    assert result.output == "recovered"
    entry = result.state.memory.history(node="slow")[-1]
    assert (entry.data["choice"], entry.data["details"]) == (
        "timeout",
        "timed out after 0.1s",
    )


@pytest.mark.asyncio
async def test_an_unhandled_timeout_fails_the_run():
    async def slow(state):
        await asyncio.sleep(10)

    graph = build(
        "nodes: [{name: slow, type: action, fn: slow, timeout: 0.1}]", {"slow": slow}
    )
    result = await graph.run()
    assert result.status == GraphStatus.FAILED
    assert result.error == "TimeoutError: Node slow timed out after 0.1s"


@pytest.mark.asyncio
async def test_retries_start_each_attempt_from_where_the_node_started():
    attempts = []

    def flaky(state):
        attempts.append(state.current_id)
        state.commit(f"attempt {len(attempts)}")
        if len(attempts) < 3:
            raise ValueError("flaky")
        return "done"

    graph = build(
        """
        nodes:
          - {name: seed, type: action, fn: seed}
          - {name: flaky, type: action, fn: flaky, retries: 2}
        """,
        {"seed": lambda state: state.commit("seed").id, "flaky": flaky},
    )
    result = await graph.run()
    assert result.status == GraphStatus.COMPLETED, result.error
    # Every attempt started from the seed, and the failed ones' commits are
    # abandoned in the tree.
    seed = result.state.tree.root.id
    assert attempts == [seed, seed, seed]
    assert result.state.tree.parent(result.state.current_id).id == seed
    assert len(result.state.tree) == 4
    failed = [
        (e.data["attempt"], e.data["details"])
        for e in result.state.memory.history(node="flaky")
        if "attempt" in e.data
    ]
    assert failed == [(1, "ValueError: flaky"), (2, "ValueError: flaky")]


@pytest.mark.asyncio
async def test_an_error_after_the_retries_takes_the_error_choice():
    def broken(state):
        raise ValueError("boom")

    graph = build(
        """
        nodes:
          - name: broken
            type: action
            fn: broken
            retries: 1
            exit: {error: end}
        """,
        {"broken": broken},
    )
    result = await graph.run()
    assert result.status == GraphStatus.COMPLETED
    assert result.state.memory.history(node="broken")[-1].data["details"] == (
        "ValueError: boom"
    )


@pytest.mark.asyncio
async def test_a_choice_is_an_outcome_never_retried():
    calls = []

    def check(state):
        calls.append(1)
        return False, "nope"

    graph = build(
        """
        nodes:
          - name: guard
            type: guardrail
            checks: [check]
            retries: 3
            exit: {fail: end}
        """,
        {"check": check},
    )
    await graph.run()
    assert calls == [1]


def test_durations():
    nodes = yaml.safe_load(
        """
        - {name: a, type: action, fn: f, timeout: 90}
        - {name: b, type: action, fn: f, timeout: 30s}
        - {name: c, type: action, fn: f, timeout: 2m}
        - {name: d, type: action, fn: f, timeout: 1.5h}
        """
    )
    timeouts = [Pipeline.model_validate({"nodes": [n]}).nodes[0].timeout for n in nodes]
    assert timeouts == [90, 30, 120, 5400]
    with pytest.raises(ValueError, match="like 30s, 10m, 2h"):
        Pipeline.model_validate(
            {"nodes": [{"name": "a", "type": "action", "fn": "f", "timeout": "1d"}]}
        )


# Runtimes.


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@pytest.mark.asyncio
async def test_a_timeout_ends_everything_running_in_the_runtime(tmp_path):
    # A command whose child outlives it, as a shell running a training
    # script does.
    async def start(state):
        await state.runtime.exec(
            "sh", ["-c", "sleep 30 & echo $! > child; wait"], cwd="/out"
        )

    graph = build(
        """
        inputs: [out]
        runtimes:
          dev: {type: host, mounts: [{path: /out, source: "${inputs.out}", readonly: false}]}
        nodes:
          - {name: start, type: action, fn: start, runtime: dev, timeout: 1, exit: {timeout: end}}
        """,
        {"start": start},
    )
    result = await graph.run(inputs={"out": str(tmp_path)})
    assert result.status == GraphStatus.COMPLETED, result.error
    child = int((tmp_path / "child").read_text())
    for _ in range(50):
        if not pid_alive(child):
            break
        await asyncio.sleep(0.1)
    assert not pid_alive(child)


@pytest.mark.asyncio
async def test_functions_run_commands_and_files_in_their_runtime(tmp_path):
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "input.txt").write_text("hello")
    roots = []

    async def work(state):
        runtime = state.runtime
        roots.append(runtime.host("/work"))
        await runtime.write("/work/script.py", "print(open('/data/input.txt').read())")
        # python is the engine's interpreter, and guest paths in arguments
        # are mapped to the host.
        run = await runtime.exec(
            "python",
            ["-c", "import sys; print(open(sys.argv[1]).read())", "/data/input.txt"],
        )
        assert await runtime.read("/work/script.py")
        return run.stdout.strip()

    graph = build(
        """
        inputs: [data]
        runtimes:
          dev: {type: host, mounts: [{path: /data, source: "${inputs.data}"}]}
        nodes: [{name: work, type: action, fn: work, runtime: dev}]
        """,
        {"work": work},
    )
    result = await graph.run(inputs={"data": str(tmp_path / "data")})
    assert result.status == GraphStatus.COMPLETED, result.error
    assert result.output == "hello"
    # The runtime was removed when the node ended.
    assert not Path(roots[0]).exists()


@pytest.mark.asyncio
async def test_a_node_without_a_runtime_has_none():
    def work(state):
        return state.runtime

    result = await build(
        "nodes: [{name: work, type: action, fn: work}]", {"work": work}
    ).run()
    assert result.status == GraphStatus.FAILED
    assert "Node work has no runtime" in result.error


def test_runtimes_are_checked_when_built():
    nodes = "nodes: [{name: work, type: action, fn: work, runtime: dev}]"
    fns = {"work": lambda state: None}
    with pytest.raises(ValueError, match="runtime 'dev', which the pipeline's"):
        build(nodes, fns)
    with pytest.raises(ValueError, match="type 'vm', expected one of"):
        build("runtimes: {dev: {type: vm}}\n" + nodes, fns)
    with pytest.raises(
        ValueError, match=r"mounts \$\{inputs.data\} at /data, which is not"
    ):
        build(
            'runtimes: {dev: {type: host, mounts: [{path: /data, source: "${inputs.data}"}]}}\n'
            + nodes,
            fns,
        )


def test_mounts_are_checked():
    def spec(*mounts):
        return RuntimeSpec(type="host", mounts=list(mounts))

    with pytest.raises(ValueError, match="must be absolute"):
        spec({"path": "data", "source": "a"})
    with pytest.raises(ValueError, match="Mounts repeat paths: /data"):
        spec({"path": "/data", "source": "a"}, {"path": "/data", "source": "b"})
    assert spec({"path": "/data", "source": "${inputs.b}"}).mounts[0].readonly
    nodes = "nodes: [{name: w, type: action, fn: w, runtime: dev}]"
    with pytest.raises(ValueError, match="a reference is"):
        build(
            'runtimes: {dev: {type: host, mounts: [{path: /d, source: "${input.d}"}]}}\n'
            + nodes,
            {"w": lambda state: None},
        )


# Mutation.


def test_mutation_only_tightens_limits():
    def pipeline(**node):
        return Pipeline.model_validate(
            {
                "runtimes": {"dev": {"type": "host"}, "vm": {"type": "microsandbox"}},
                "nodes": [
                    {"name": "a", "type": "action", "fn": "f", "mutable": True, **node}
                ],
            }
        )

    original = pipeline(timeout=60, retries=2, runtime="dev")
    check_mutation(original, pipeline(timeout=30, retries=1, runtime="dev"))
    for change, error in [
        ({"timeout": 120, "retries": 2, "runtime": "dev"}, "longer timeout"),
        ({"retries": 2, "runtime": "dev"}, "longer timeout"),
        ({"timeout": 60, "retries": 3, "runtime": "dev"}, "more retries"),
        ({"timeout": 60, "retries": 2, "runtime": "vm"}, "another runtime"),
    ]:
        with pytest.raises(ValueError, match=error):
            check_mutation(original, pipeline(**change))
    changed = pipeline(timeout=60, retries=2, runtime="dev")
    changed.runtimes["dev"] = RuntimeSpec(type="host", cpus=8)
    with pytest.raises(ValueError, match="runtimes were changed"):
        check_mutation(original, changed)


# The microsandbox backend, with a stand-in for its SDK.


class FakeSandbox:
    def __init__(self, calls):
        self.calls = calls
        self.fs = types.SimpleNamespace(write=self.write, read=self.read)

    async def exec(self, cmd, args, **kwargs):
        self.calls.append(("exec", cmd, args, kwargs))
        if kwargs.get("timeout") == 0.1:
            raise FakeExecTimeout()
        return types.SimpleNamespace(exit_code=0, stdout_text="out", stderr_text="")

    async def write(self, path, data):
        self.calls.append(("write", path, data))

    async def read(self, path):
        return b"content"

    async def stop(self, timeout=None):
        self.calls.append(("stop", timeout))

    async def kill(self, timeout=None):
        self.calls.append(("kill",))


class FakeExecTimeout(Exception):
    pass


@pytest.fixture
def fake_sdk(monkeypatch):
    calls = []

    class Sandbox:
        @staticmethod
        async def create(name, **kwargs):
            calls.append(("create", name, kwargs))
            return FakeSandbox(calls)

        @staticmethod
        async def remove(name):
            calls.append(("remove", name))

    class Volume:
        @staticmethod
        def bind(path, readonly=False):
            return ("bind", path, readonly)

    module = types.SimpleNamespace(
        Sandbox=Sandbox, Volume=Volume, ExecTimeoutError=FakeExecTimeout
    )
    monkeypatch.setitem(sys.modules, "microsandbox", module)
    return calls


@pytest.mark.asyncio
async def test_microsandbox_backend(fake_sdk):
    spec = RuntimeSpec(type="microsandbox", image="python", cpus=2, memory=1024)
    runtime = await MicrosandboxBackend().create(
        "swarm-a-1", spec, [Mount(host="/data", guest="/data")], max_duration=70
    )
    run = await runtime.exec("python", ["-c", "1"])
    timed_out = await runtime.exec("sleep", ["9"], timeout=0.1)
    await runtime.write("/work/a.txt", "a")
    await runtime.stop(10)
    await runtime.remove()

    name, kwargs = fake_sdk[0][1], fake_sdk[0][2]
    assert name == "swarm-a-1"
    assert kwargs["image"] == "python" and kwargs["cpus"] == 2
    assert kwargs["memory"] == 1024 and kwargs["max_duration"] == 70
    assert kwargs["workdir"] == "/work"
    assert kwargs["volumes"] == {"/data": ("bind", "/data", True)}
    assert (run.exit_code, run.stdout) == (0, "out")
    assert timed_out.timed_out and timed_out.exit_code is None
    assert ("write", "/work/a.txt", b"a") in fake_sdk
    assert fake_sdk[-2:] == [("stop", 10), ("remove", "swarm-a-1")]
