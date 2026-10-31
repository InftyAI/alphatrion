import asyncio
import contextlib
import enum
import logging
import re
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from opentelemetry import trace
from pydantic import BaseModel, ConfigDict

from alphatrion.swarm import tracing
from alphatrion.swarm.context import (
    current_inputs,
    current_iterations,
    output_scope,
    run_inputs,
    using_runtime,
    using_store,
)
from alphatrion.swarm.formats import (
    Metrics,
    ModelResponse,
    check_value,
    describe,
    unify,
)
from alphatrion.swarm.nodes import Node, NodeResult
from alphatrion.swarm.nodes.base import NO_OUTPUT, Choice
from alphatrion.swarm.runtimes import Runtime
from alphatrion.swarm.state import State
from alphatrion.swarm.store import RunStore

# Exits, the targets of edges that leave a graph. end finishes the current
# run and raise fails it, from anywhere inside it. A run is the top graph,
# or a branch of a parallel node, so neither affects the other branches.
END = "end"
RAISE = "raise"
# Exits of a loop body: continue discards the iteration and starts the next
# one, and break ends the loop.
CONTINUE = "continue"
BREAK = "break"
# Internal exits: the natural end of a loop body, which carries its value
# into the next iteration, and of a parallel branch body.
NEXT = "__next__"
DONE = "__done__"
RESERVED = {END, RAISE, CONTINUE, BREAK, NEXT, DONE}
# The choices of a node that failed, after its retries: it ran past its
# timeout, or raised. Every node has them, and a run fails on one the node
# doesn't handle. The value passes through, as the node never produced one.
TIMEOUT = "timeout"
ERROR = "error"
FAILURES = (TIMEOUT, ERROR)
# How long a runtime has to stop before it is killed.
STOP_GRACE = 10.0


class Edge(BaseModel):
    source: str
    target: str
    when: str | None = None


class GraphStatus(enum.Enum):
    # Reached END or another exit, or a node without outgoing edges.
    COMPLETED = "completed"
    # A node raised an exception, or took the raise exit.
    FAILED = "failed"


class GraphResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    status: GraphStatus
    state: State
    # The names of the executed nodes, in order.
    path: list[str]
    # The exit reached when completed: END, or one of the graph's exits.
    exit: str | None = None
    # The value the graph ended with, the output of its last node.
    output: Any = None
    error: str | None = None


class ChoiceError(Exception):
    pass


class Graph:
    """
    A directed acyclic graph of nodes. Execution starts at the entry node,
    and after each node, follows the outgoing edge whose `when` matches the
    node choice, or the default edge (when=None) if no edge matches.

    Cycles are rejected: repetition is a LoopNode, bounded by its own
    max_iters, so a graph always ends unless one of its nodes runs forever.

    A value flows along the edges: each node receives the output of the node
    before it, and the entry node the value the graph runs with. Every edge
    is checked when the graph is validated: the output format of its source
    must match the input format of its target.

    Each execution is recorded in the state memory.
    """

    def __init__(
        self,
        name: str = "graph",
        exits: set[str] | None = None,
        scope: str | None = None,
        inputs: set[str] | None = None,
    ):
        """
        :param exits: targets, besides END, that end the graph, e.g. CONTINUE
            and BREAK in a loop body. The reached one is GraphResult.exit.
        :param scope: qualifies the node names recorded in memory, e.g. the
            nodes of a subgraph named experiment as experiment.<name>.
        :param inputs: the inputs a run must be given, the pipeline's.
        """
        self.name = name
        self.inputs: set[str] = set(inputs or ())
        self.scope = scope
        self.exits = {END, RAISE, *(exits or ())}
        self.entry: str | None = None
        self._nodes: dict[str, Node] = {}
        self._edges: dict[str, list[Edge]] = {}
        # Validation is cached, since loop bodies run once per iteration.
        self._validated = False

    @property
    def nodes(self) -> dict[str, Node]:
        return dict(self._nodes)

    @property
    def edges(self) -> list[Edge]:
        return [e for edges in self._edges.values() for e in edges]

    def add_node(self, node: Node, entry: bool = False) -> "Graph":
        if node.name in RESERVED:
            raise ValueError(f"{node.name!r} is reserved and can't be a node name")
        if node.name in self._nodes:
            raise ValueError(f"Node {node.name} already exists")
        if not node.prepared:
            # Nodes built in code don't go through a pipeline Builder, so
            # prepare them with one that resolves functions and import paths.
            from alphatrion.swarm.pipeline import Builder

            # It references the nodes added before it.
            builder = Builder(inputs=self.inputs)
            builder._available = dict(self._nodes)
            builder.node(node)
        self._nodes[node.name] = node
        self._validated = False
        self._edges[node.name] = []
        if entry or self.entry is None:
            self.entry = node.name
        return self

    def add_edge(self, source: str, target: str, when: str | None = None) -> "Graph":
        if source not in self._nodes:
            raise KeyError(f"Source node {source} not found")
        if target not in self.exits and target not in self._nodes:
            raise KeyError(f"Target node {target} not found")
        if any(e.when == when for e in self._edges[source]):
            raise ValueError(f"Node {source} already has an edge with when={when!r}")
        self._edges[source].append(Edge(source=source, target=target, when=when))
        self._validated = False
        return self

    def set_entry(self, name: str) -> "Graph":
        if name not in self._nodes:
            raise KeyError(f"Entry node {name} not found")
        self.entry = name
        return self

    def validate(self) -> None:
        if self._validated:
            return
        if self.entry is None:
            raise ValueError(f"Graph {self.name} has no nodes")
        for name, node in self._nodes.items():
            choices = {e.when for e in self._edges[name]}
            missing = node.required_choices - choices
            if missing:
                raise ValueError(
                    f"Node {name} requires edges for choices {sorted(missing)}"
                )
        cycle = self._find_cycle()
        if cycle:
            raise ValueError(
                f"Graph {self.name} has a cycle {' -> '.join(cycle)}, "
                "use a LoopNode to repeat nodes"
            )
        self._validated = True

    @property
    def output_type(self) -> Any:
        """The format of the graph's output, its last output: the outputs of
        the nodes it can end after, Any if they differ."""
        formats = []
        for name, edges in self._edges.items():
            node = self._nodes[name]
            for edge in edges:
                if edge.target not in (END, NEXT, DONE) or edge.when in FAILURES:
                    continue
                fmt = node.output_type() if node.outputs_on(edge.when) else None
                # Ending after a decision, the last output is an earlier one.
                formats.append(Any if fmt is None else fmt)
        return unify(formats)

    def describe(self) -> str:
        """
        Each node, in the order they run, with what it outputs, what it's
        given: its params, with the references to the outputs it takes, its
        runtime, timeout and retries, and where its choices go. The nodes nested in a loop, a parallel node or
        a subgraph are indented under it. Built from the graph itself, it
        is always what runs.
        """
        self.validate()
        rows: list[tuple[str, str, str]] = []
        self._describe(rows, 0)
        width = max(len(name) for name, _, _ in rows)
        flow = max(len(io) for _, io, _ in rows)
        return "\n".join(
            f"{name:<{width}}  {io:<{flow}}  {notes}".rstrip()
            for name, io, notes in rows
        )

    def _describe(self, rows: list[tuple[str, str, str]], depth: int) -> None:
        order = self._topological_order()
        for name in order:
            node = self._nodes[name]
            output = node.output_type()
            io = "" if output is None else f"-> {_name(output)}"
            notes = [node.type]
            for key in ("max_iters", "n", "join", "wait"):
                if getattr(node, key, None) is not None:
                    notes.append(f"{key}: {getattr(node, key)}")
            if node.params:
                notes.append(
                    "params: " + ", ".join(f"{k}={v}" for k, v in node.params.items())
                )
            if node.runtime is not None:
                notes.append(f"runtime: {node.runtime}")
            if node.timeout is not None:
                notes.append(f"timeout: {node.timeout:g}s")
            if node.retries:
                notes.append(f"retries: {node.retries}")
            choices = [
                f"{edge.when} -> {edge.target}"
                for edge in self._edges[name]
                if edge.when is not None
            ]
            default = next(e for e in self._edges[name] if e.when is None)
            # Running off the last node ends the graph, which goes unsaid.
            ends = default.target == END and name == order[-1]
            if default.target in (END, RAISE, CONTINUE, BREAK) and not ends:
                choices.append(f"-> {default.target}")
            if choices:
                notes.append("choices: " + ", ".join(choices))
            rows.append(("  " * depth + name, io, "  ".join(notes)))
            nested = getattr(node, "_graph", None)
            if isinstance(nested, Graph):
                nested._describe(rows, depth + 1)

    def _topological_order(self) -> list[str]:
        indegree = {name: 0 for name in self._nodes}
        for edge in self.edges:
            if edge.target in indegree:
                indegree[edge.target] += 1
        ready = [name for name, degree in indegree.items() if degree == 0]
        order = []
        while ready:
            name = ready.pop(0)
            order.append(name)
            for edge in self._edges[name]:
                if edge.target in indegree:
                    indegree[edge.target] -= 1
                    if indegree[edge.target] == 0:
                        ready.append(edge.target)
        return order

    def _find_cycle(self) -> list[str] | None:
        """Return the nodes of a cycle, or None if the graph is acyclic."""
        visiting, done = set(), set()

        def visit(name: str, path: list[str]) -> list[str] | None:
            if name in visiting:
                return path[path.index(name) :] + [name]
            if name in done or name in self.exits:
                return None
            visiting.add(name)
            for edge in self._edges[name]:
                cycle = visit(edge.target, path + [name])
                if cycle:
                    return cycle
            visiting.discard(name)
            done.add(name)
            return None

        for name in self._nodes:
            cycle = visit(name, [])
            if cycle:
                return cycle
        return None

    def next(self, source: str, result: NodeResult) -> str:
        """Return the next node name, or END."""
        edges = self._edges[source]
        if not edges:
            return END
        default = None
        for edge in edges:
            if edge.when is not None and edge.when == result.choice:
                return edge.target
            if edge.when is None:
                default = edge
        if default is not None:
            return default.target
        raise ChoiceError(f"Node {source} has no edge for choice {result.choice!r}")

    async def run(
        self,
        state: State | None = None,
        inputs: dict[str, Any] | None = None,
        store: RunStore | None = None,
    ) -> GraphResult:
        """
        Run the graph. Pass a state to continue from an existing memory and
        tree, e.g. one loaded from a previous run. inputs are the run's, e.g.
        a data directory, which nodes reference as ${inputs.name}. A nested
        run, e.g. a loop body, keeps the inputs of the run it's part of, and
        sees the outputs before it. The result's output is the run's last
        output. A store, e.g. HostStore("runs"), keeps the run: its
        artifacts, metrics, requests, tree and memory.
        """
        self.validate()
        if state is None:
            state = State()
        with run_inputs(inputs) as given:
            missing = self.inputs - set(given)
            if missing:
                return GraphResult(
                    status=GraphStatus.FAILED,
                    state=state,
                    path=[],
                    error=f"The run is missing inputs: {', '.join(sorted(missing))}",
                )
            if store is not None:
                store.start(self, given)
                # A continued state's artifacts are kept too.
                for artifact in state.tree:
                    store.artifact(artifact, state.tree)
                with using_store(store):
                    result = await self.run(state=state)
                store.finish(result, state)
                return result
            with (
                output_scope() as outputs,
                tracing.tracer().start_as_current_span(f"run {self.name}") as span,
            ):
                span.set_attribute(tracing.KIND, tracing.CHAIN)
                span.set_attribute("swarm.graph", self.name)
                if state.branch is not None:
                    span.set_attribute("swarm.branch", state.branch)
                result = await self._run(state, outputs)
                span.set_attribute("swarm.status", result.status.value)
                if result.error:
                    span.set_status(trace.Status(trace.StatusCode.ERROR, result.error))
                return result

    async def _run(self, state: State, outputs: dict[str, Any]) -> GraphResult:
        path: list[str] = []
        # The last output, the run's.
        value = None
        current = self.entry
        while True:
            node = self._nodes[current]
            state.node = self._qualified(node)
            path.append(node.name)

            try:
                started = time.monotonic()
                result = await self._execute(node, state)
                _log_step(state, result, time.monotonic() - started)
                # A node has an output only with the choices it outputs on, checked against
                # its format, which the nodes referencing it were checked
                # against when the graph was built.
                produced = (
                    result.choice not in FAILURES
                    and node.outputs_on(result.choice)
                    and result.output is not NO_OUTPUT
                )
                if produced:
                    try:
                        result.output = check_value(result.output, node.output_type())
                    except TypeError as e:
                        raise TypeError(
                            f"Node {node.name} returned the wrong format, {e}"
                        ) from None
                else:
                    result.output = None
                current = self.next(node.name, result)
            except Exception as e:
                error = f"{type(e).__name__}: {e}"
                self._record(state, node, {"error": error})
                return GraphResult(
                    status=GraphStatus.FAILED,
                    state=state,
                    path=path,
                    output=value,
                    error=error,
                )
            finally:
                state.node = None

            self._record(
                state,
                node,
                {
                    "choice": result.choice,
                    "output": result.output,
                    "details": result.details,
                    "artifact_id": state.current_id,
                },
            )
            if produced:
                outputs[node.name] = result.output
                value = result.output
            state.step += 1
            # Yield to the event loop, so parallel branches interleave even
            # when their nodes are sync functions.
            await asyncio.sleep(0)
            if current == RAISE:
                error = f"{node.name} raised on choice {result.choice!r}"
                if result.details not in (None, [], ""):
                    error += f": {result.details}"
                return GraphResult(
                    status=GraphStatus.FAILED,
                    state=state,
                    path=path,
                    output=value,
                    error=error,
                )
            if result.exit == END:
                current = END
            if current in self.exits:
                return GraphResult(
                    status=GraphStatus.COMPLETED,
                    state=state,
                    path=path,
                    exit=current,
                    output=value,
                )

    async def _execute(self, node: Node, state: State) -> NodeResult:
        """
        Run a node, up to 1 + retries times, each from where it started: in
        a fresh runtime if it has one, and cancelled at its timeout. A node
        still failing takes its timeout or error choice if it handles it, and
        fails the run otherwise.
        """
        start = state.current_id
        for attempt in range(1, node.retries + 2):
            limit = None
            with tracing.tracer().start_as_current_span(f"node {state.node}") as span:
                span.set_attribute(tracing.KIND, tracing.CHAIN)
                span.set_attribute("swarm.node", state.node)
                span.set_attribute("swarm.node.type", node.type)
                span.set_attribute("swarm.attempt", attempt)
                for loop, iteration in current_iterations().items():
                    span.set_attribute(f"swarm.iteration.{loop}", iteration)
                if state.branch is not None:
                    span.set_attribute("swarm.branch", state.branch)
                try:
                    async with self._runtime(node):
                        async with asyncio.timeout(node.timeout) as limit:
                            result = await node.call(state)
                    if result.choice is not None:
                        span.set_attribute("swarm.choice", result.choice)
                    return result
                except Choice as choice:
                    # A choice the node's function made: an outcome, not
                    # retried.
                    span.set_attribute("swarm.choice", choice.choice)
                    return NodeResult(choice=choice.choice, details=choice.details)
                except Exception as e:
                    if (
                        isinstance(e, TimeoutError)
                        and limit is not None
                        and limit.expired()
                    ):
                        failure, details = (
                            TIMEOUT,
                            f"timed out after {node.timeout:g}s",
                        )
                    else:
                        failure, details = ERROR, f"{type(e).__name__}: {e}"
                    last = e
                    span.set_attribute("swarm.choice", failure)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, details))
            # An attempt that committed is abandoned: its artifacts stay in
            # the tree, but the next attempt starts from the same one.
            state.current_id = start
            if attempt <= node.retries:
                self._record(
                    state,
                    node,
                    {"attempt": attempt, "choice": failure, "details": details},
                )
        if any(edge.when == failure for edge in self._edges[node.name]):
            return NodeResult(choice=failure, details=details)
        if failure == TIMEOUT:
            raise TimeoutError(f"Node {node.name} {details}")
        raise last

    @asynccontextmanager
    async def _runtime(self, node: Node) -> AsyncIterator[None]:
        """The node's runtime for one attempt, created for it and stopped
        when it ends, killed if it doesn't stop in time, so nothing it ran
        outlives the attempt."""
        plan = node._runtime
        if plan is None:
            yield
            return
        name = f"swarm-{re.sub(r'[^a-z0-9-]', '-', node.name.lower())}-{uuid.uuid4().hex[:8]}"
        # The backend's own deadline, should the engine's process die.
        deadline = node.timeout + STOP_GRACE if node.timeout is not None else None
        runtime = await plan.backend.create(
            name, plan.spec, plan.mounts(current_inputs()), deadline
        )
        try:
            with using_runtime(runtime):
                yield
        finally:
            await _close(runtime)

    def _qualified(self, node: Node) -> str:
        return f"{self.scope}.{node.name}" if self.scope else node.name

    def _record(self, state: State, node: Node, data: dict[str, Any]) -> None:
        if state.branch is not None:
            data["branch"] = state.branch
        iterations = current_iterations()
        if iterations:
            data["iteration"] = iterations
        state.memory.record(state.step, self._qualified(node), node.type, data)


async def _close(runtime: Runtime) -> None:
    try:
        await asyncio.wait_for(runtime.stop(STOP_GRACE), STOP_GRACE + 1)
    except Exception:
        with contextlib.suppress(Exception):
            await runtime.kill()
    finally:
        with contextlib.suppress(Exception):
            await runtime.remove()


def _name(fmt: Any) -> str:
    return "any" if fmt is Any else describe(fmt)


# Each node that ran, at INFO, e.g. to follow a long run as it goes.
logger = logging.getLogger("alphatrion.swarm")


def _log_step(state: State, result: NodeResult, seconds: float) -> None:
    if not logger.isEnabledFor(logging.INFO):
        return
    where = " ".join(f"{loop} {i}" for loop, i in current_iterations().items())
    output = result.output
    if isinstance(output, Metrics):
        detail = f"{output.primary} {output.score:.4f}"
    elif isinstance(output, ModelResponse):
        detail = f"{output.model}, {output.output_tokens or '?'} tokens"
    elif result.choice is not None:
        detail = result.choice
        if result.details not in (None, "", []):
            detail += f": {str(result.details).splitlines()[0][:120]}"
    else:
        detail = ""
    logger.info(
        "%s%-10s %6.1fs  %s",
        f"[{where}] " if where else "",
        state.node,
        seconds,
        detail,
    )
