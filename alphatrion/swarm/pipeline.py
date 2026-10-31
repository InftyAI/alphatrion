import importlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from alphatrion.swarm.capabilities import Capability
from alphatrion.swarm.graph import BREAK, CONTINUE, END, FAILURES, RAISE, Graph
from alphatrion.swarm.nodes import (
    FnRef,
    Node,
    NodeFn,
    NodeList,
    SubgraphNode,
)
from alphatrion.swarm.nodes.base import reference
from alphatrion.swarm.runtimes import (
    BUILTIN_BACKENDS,
    Backend,
    MountSpec,
    RuntimePlan,
    RuntimeSpec,
)

# The only targets of exit: there is no goto, branches nest instead.
EXITS = (END, RAISE, CONTINUE, BREAK)


class Pipeline(BaseModel):
    """The definition of a graph, written like structured code: nodes run in
    order, branches nest the nodes to run for a choice, loop and parallel nodes
    nest repeated and concurrent nodes, and end, continue and break are the
    only jumps."""

    model_config = ConfigDict(extra="forbid")

    name: str = "graph"
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Settings shared by the nodes, e.g. a command, which a node "
        "gives its function with ${params.name} in its params.",
    )
    inputs: list[str] = Field(
        default_factory=list,
        description="The inputs a run must be given, e.g. a data directory, "
        "which a node gives its function with ${inputs.name} in its params, "
        "or a runtime mounts.",
    )
    runtimes: dict[str, RuntimeSpec] = Field(
        default_factory=dict,
        description="Runtimes by name, which nodes run in with runtime: name, "
        "e.g. a microVM or a Kubernetes pod. They are part of the fixed root: "
        "nodes choose one, never change it.",
    )
    nodes: NodeList

    # The file the pipeline was loaded from, if any.
    _file: Path | None = PrivateAttr(default=None)


class Builder:
    """Prepares nodes and builds graphs from them, resolving function
    references. Nodes use it to resolve their functions and build the
    graphs they nest."""

    def __init__(
        self,
        functions: dict[str, NodeFn] | None = None,
        node_types: list[type[Node]] | None = None,
        base_dir: str | Path | None = None,
        params: dict[str, Any] | None = None,
        inputs: list[str] | None = None,
        runtimes: dict[str, RuntimeSpec] | None = None,
        backends: list[Backend] | None = None,
    ):
        """
        :param node_types: custom node types, for the pipelines subgraphs
            load from files.
        :param base_dir: where pipeline files referenced by subgraphs are,
            the directory of the pipeline file being built.
        :param params: the pipeline's params, injected into node functions.
        :param inputs: the pipeline's inputs, injected into node functions.
        :param runtimes: the pipeline's runtimes, by name.
        :param backends: custom backends, besides the built-in ones.
        """
        self.functions = functions or {}
        self.params: dict[str, Any] = dict(params or {})
        self.inputs: set[str] = set(inputs or [])
        self.runtimes: dict[str, RuntimeSpec] = dict(runtimes or {})
        self.backends: dict[str, Backend] = {
            **BUILTIN_BACKENDS,
            **{backend.type: backend for backend in backends or []},
        }
        self.node_types = node_types
        self._base_dir = Path(base_dir) if base_dir is not None else Path.cwd()
        # Names are unique within a pipeline, nested nodes included, since
        # the memory history identifies nodes by name. A subgraph has a scope
        # of its own, so its nodes are recorded as <subgraph>.<name>.
        self._names: set[str] = set()
        self._scope: str | None = None
        self._loading: list[Path] = []
        # The nodes the node being built can reference: those that always
        # run before it, and always have an output when they do.
        self._available: dict[str, Node] = {}

    def resolve(self, ref: FnRef) -> NodeFn:
        if callable(ref):
            return ref
        if ref in self.functions:
            return self.functions[ref]
        if ":" not in ref:
            raise KeyError(
                f"Function {ref!r} is not registered, "
                "register it or use an import path like 'package.module:func'"
            )
        module_name, _, attr = ref.partition(":")
        fn = getattr(importlib.import_module(module_name), attr)
        if not callable(fn):
            raise TypeError(f"{ref} is not callable")
        return fn

    def runtime(self, node: str, name: str) -> RuntimePlan:
        """Resolve the runtime a node runs in: its backend, and its mounts,
        relative to the pipeline file or inputs of the pipeline."""
        spec = self.runtimes.get(name)
        if spec is None:
            raise ValueError(
                f"Node {node} runs in runtime {name!r}, which the pipeline's "
                f"runtimes don't have: {', '.join(sorted(self.runtimes)) or 'none'}"
            )
        backend = self.backends.get(spec.type)
        if backend is None:
            raise ValueError(
                f"Runtime {name} has type {spec.type!r}, expected one of "
                f"{sorted(self.backends)} or a backend passed to "
                "build_graph(backends=...)"
            )
        mounts: list[tuple[MountSpec, str | None]] = []
        for mount in spec.mounts:
            source, key = reference(f"Runtime {name} mount {mount.path}", mount.source)
            if source == "inputs":
                if key not in self.inputs:
                    raise ValueError(
                        f"Runtime {name} mounts ${{inputs.{key}}} at {mount.path}, "
                        "which is not an input of the pipeline"
                    )
                mounts.append((mount, key))
                continue
            if source == "params":
                if key not in self.params:
                    raise ValueError(
                        f"Runtime {name} mounts ${{params.{key}}} at {mount.path}, "
                        "which is not a param of the pipeline"
                    )
                path = str(self.params[key])
            else:
                path = mount.source
            # Paths are relative to the pipeline file.
            host = str((self._base_dir / path).resolve())
            mounts.append((mount.model_copy(update={"source": host}), None))
        return RuntimePlan(backend, spec, mounts)

    def output_of(self, where: str, name: str) -> Any:
        """The output format of the node a reference ${nodes.name.output}
        names, which must always run before the node referencing it, with an
        output: earlier in the same block, or before the block, but not in a
        branch it may skip, nor a node that has none, like a decision."""
        node = self._available.get(name)
        if node is None:
            raise ValueError(
                f"{where} is ${{nodes.{name}.output}}, but {name} is not a node "
                "that always runs before it with an output"
            )
        return node.output_type()

    def node(self, node: Node) -> Node:
        if node.name in self._names:
            raise ValueError(f"Node name {node.name} is used more than once")
        self._names.add(node.name)
        node.prepare(self)
        return node

    def graph(
        self,
        name: str,
        nodes: list[Node],
        exits: set[str] | None = None,
        after: str = END,
    ) -> Graph:
        """Build a graph from a list of nodes. exits are the exits allowed
        besides END and RAISE, e.g. CONTINUE and BREAK in a loop body, and
        after is where running off the end of the nodes goes."""
        graph = Graph(name=name, exits=exits, scope=self._scope, inputs=self.inputs)
        graph.set_entry(self._block(graph, nodes, after))
        graph.validate()
        return graph

    def subgraph(
        self, name: str, nodes: list[Node] | None = None, path: str | None = None
    ) -> Graph:
        """Build the graph of a subgraph node, from its nodes or from the
        pipeline file at path, relative to the pipeline referencing it. The
        subgraph has a name scope of its own, so it can be used more than
        once."""
        saved = (
            self._names,
            self._scope,
            self._base_dir,
            self.params,
            self.inputs,
            self.runtimes,
        )
        self._names = set()
        self._scope = f"{self._scope}.{name}" if self._scope else name
        try:
            if path is None:
                return self.graph(name, nodes)
            file = (self._base_dir / path).resolve()
            if file in self._loading:
                raise ValueError(f"Pipeline {file} includes itself")
            self._loading.append(file)
            self._base_dir = file.parent
            sub = load_pipeline(file, self.node_types)
            # A subgraph file's params are defaults the parent's override,
            # and its inputs are the parent's too.
            self.params = {**sub.params, **self.params}
            self.inputs = self.inputs | set(sub.inputs)
            self.runtimes = {**sub.runtimes, **self.runtimes}
            try:
                return self.graph(name, sub.nodes)
            finally:
                self._loading.pop()
        finally:
            (
                self._names,
                self._scope,
                self._base_dir,
                self.params,
                self.inputs,
                self.runtimes,
            ) = saved

    def _block(self, graph: Graph, nodes: list[Node], after: str) -> str:
        """Add a block of nodes to the graph, so that it runs them in order
        and then goes to after. Returns the name of its first node.

        The block is built backwards, so the node each one continues with
        is already in the graph when it is wired."""
        if not nodes:
            raise ValueError(f"Graph {graph.name} has an empty block of nodes")
        # Each node can reference the nodes before the block, and those
        # earlier in it that always have an output, unless a branch may
        # bypass them, as after a choice the node made it has none.
        outer = self._available
        running = dict(outer)
        before: dict[str, dict[str, Node]] = {}
        for node in nodes:
            before[node.name] = self._available = dict(running)
            self.node(node)
            if node.output_type() is not None and not node.branches:
                running[node.name] = node
        self._available = outer
        for node in reversed(nodes):
            graph.add_node(node)
            choices = node.exit if isinstance(node.exit, dict) else {}
            self._check_choices(node, [*choices, *node.branches])
            for choice, target in choices.items():
                if choice in node.branches:
                    raise ValueError(
                        f"Node {node.name} choice {choice!r} has both an exit "
                        "and a branch"
                    )
                if choice != "default":
                    graph.add_edge(node.name, self._exit(graph, node, target), choice)
            for choice, branch in node.branches.items():
                # An empty branch does nothing and continues with after. A
                # branch sees what its node did, without the node's output.
                self._available = before[node.name]
                target = self._block(graph, branch, after) if branch else after
                self._available = outer
                graph.add_edge(node.name, target, choice)

            default = choices.get("default") or (
                node.exit if isinstance(node.exit, str) else None
            )
            target = self._exit(graph, node, default) if default else after
            graph.add_edge(node.name, target)
            after = node.name
        return after

    @staticmethod
    def _check_choices(node: Node, keys: list[str]) -> None:
        choices = node.choices
        if choices is None:
            return
        for key in keys:
            # Any node can fail on a timeout or an error.
            if key != "default" and key not in choices and key not in FAILURES:
                expected = ", ".join(sorted(choices)) or "none"
                raise ValueError(
                    f"Node {node.name} has no choice {key!r}, "
                    f"the choices of a {node.type} node are: {expected}, and "
                    "every node's timeout and error"
                )

    @staticmethod
    def _exit(graph: Graph, node: Node, target: str) -> str:
        if target not in EXITS:
            raise ValueError(
                f"Node {node.name} goes to {target!r}, but exit only takes "
                f"{', '.join(EXITS)}; use branches to run other nodes"
            )
        if target not in graph.exits:
            raise ValueError(
                f"Node {node.name} goes to {target}, which is only allowed in a loop"
            )
        return target


def _context(node_types: list[type[Node]] | None) -> dict[str, Any]:
    return {"node_types": {node.node_type(): node for node in node_types or []}}


def load_pipeline(
    path: str | Path, node_types: list[type[Node]] | None = None
) -> Pipeline:
    file = Path(path).resolve()
    pipeline = Pipeline.model_validate(
        yaml.safe_load(file.read_text()), context=_context(node_types)
    )
    pipeline._file = file
    return pipeline


def build_graph(
    pipeline: Pipeline | dict[str, Any] | str | Path,
    functions: dict[str, NodeFn] | None = None,
    node_types: list[type[Node]] | None = None,
    backends: list[Backend] | None = None,
) -> Graph:
    """
    Build a graph from a pipeline, a pipeline dict, or the path of a YAML
    pipeline.

    :param functions: functions the pipeline can reference by name.
    :param node_types: classes of custom node types, they can also
        override the built-in ones.
    :param backends: custom runtime backends, e.g. for Kubernetes, which
        can also override the built-in ones.
    """
    if isinstance(pipeline, str | Path):
        pipeline = load_pipeline(pipeline, node_types)
    elif isinstance(pipeline, dict):
        pipeline = Pipeline.model_validate(pipeline, context=_context(node_types))
    # A pipeline loaded from a file, even one changed since, resolves the
    # paths in it, e.g. of subgraphs and mounts, relative to the file.
    path = pipeline._file
    base_dir = path.parent if path is not None else None
    builder = Builder(
        functions,
        node_types,
        base_dir,
        pipeline.params,
        pipeline.inputs,
        pipeline.runtimes,
        backends,
    )
    if base_dir is not None:
        builder._loading.append(path)
    return builder.graph(pipeline.name, pipeline.nodes)


def _walk(nodes: list[Node], scope: str | None = None) -> Iterator[tuple[str, Node]]:
    """Every node with its qualified name, nested ones included. Like in
    memory, the nodes of a subgraph are named <subgraph>.<name>."""
    for node in nodes:
        name = f"{scope}.{node.name}" if scope else node.name
        yield name, node
        if isinstance(node, SubgraphNode):
            yield from _walk(node.nodes or [], name)
        else:
            yield from _walk(getattr(node, "nodes", None) or [], scope)
        for branch in node.branches.values():
            yield from _walk(branch, scope)


def _definition(node: Node) -> tuple[type[Node], dict[str, Any]]:
    # serialize_as_any keeps the fields of nested node types.
    return type(node), node.model_dump(serialize_as_any=True)


def _check_limits(name: str, before: Node, after: Node) -> None:
    """A mutated node's limits only tighten: its timeout can shorten, its
    retries can drop, and its runtime never changes."""
    looser_timeout = before.timeout is not None and (
        after.timeout is None or after.timeout > before.timeout
    )
    if looser_timeout:
        raise ValueError(f"Node {name} has a longer timeout")
    if after.retries > before.retries:
        raise ValueError(f"Node {name} has more retries")
    if after.runtime != before.runtime:
        raise ValueError(f"Node {name} runs in another runtime")


def check_mutation(original: Pipeline, mutated: Pipeline) -> None:
    """
    Check that a mutated pipeline, e.g. one proposed by self-improvement,
    only changes what the original allows, and raise ValueError otherwise.

    Every immutable node of the original must still be there, by qualified
    name, with the same definition, its nested nodes included. Mutable nodes
    can change or be removed, but never gain capabilities, loosen their
    timeout or retries, or change their runtime. The runtimes never
    change. Nodes can be added, but not with the score capability: only the evaluation decides
    what counts as an improvement. A subgraph file is compared by its path,
    so the file itself must be protected.
    """
    if original.runtimes != mutated.runtimes:
        raise ValueError("The runtimes were changed, but they are never improved")
    before = dict(_walk(original.nodes))
    after = dict(_walk(mutated.nodes))
    for name, node in before.items():
        if name not in after:
            if not node.mutable:
                raise ValueError(f"Immutable node {name} was removed")
            continue
        if not node.mutable:
            if _definition(after[name]) != _definition(node):
                raise ValueError(f"Immutable node {name} was changed")
            continue
        gained = after[name].granted - node.granted
        if gained:
            raise ValueError(
                f"Node {name} gained the {', '.join(sorted(gained))} capability"
            )
        _check_limits(name, node, after[name])
    for name, node in after.items():
        if name not in before and Capability.SCORE in node.granted:
            raise ValueError(
                f"Node {name} was added with the score capability, but the "
                "evaluation is never improved"
            )


Node.model_rebuild()
