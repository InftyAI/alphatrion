import inspect
import re
from abc import abstractmethod
from collections.abc import Callable
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    ClassVar,
    get_type_hints,
)

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    PrivateAttr,
    ValidationInfo,
    field_validator,
)

from alphatrion.swarm.capabilities import Capability, StateView
from alphatrion.swarm.context import current_inputs, current_outputs
from alphatrion.swarm.formats import check_value, compatible, describe
from alphatrion.swarm.state import State

if TYPE_CHECKING:
    from alphatrion.swarm.pipeline import Builder
    from alphatrion.swarm.runtimes import RuntimePlan

# A node function takes the state and the node params, and can be sync or async.
NodeFn = Callable[..., Any]

# A function reference: a registered name or an import path in YAML, or the
# function itself in code.
FnRef = str | NodeFn


class _NoOutput:
    def __repr__(self) -> str:
        return "NO_OUTPUT"


# The output of a node that has none this time, e.g. a loop whose every
# iteration was discarded, so nothing references it.
NO_OUTPUT = _NoOutput()


class NodeResult(BaseModel):
    """The outcome of a node execution. choice selects the outgoing edge whose
    `when` matches it, None selects the default edge. exit="end" ends the
    current run, which loop nodes use to pass on an end taken inside them."""

    choice: str | None = None
    output: Any = None
    # What the node found, recorded in memory but not passed on, e.g. why a
    # guardrail failed. Passthrough nodes return their input as output.
    details: Any = None
    exit: str | None = None


async def call(fn: NodeFn, *args: Any, **kwargs: Any) -> Any:
    result = fn(*args, **kwargs)
    if inspect.isawaitable(result):
        result = await result
    return result


class Choice(Exception):
    """
    Raised by a node function to make a choice rather than output, e.g.
    raise Choice("skip", "the edits don't apply") for an exit like
    `exit: {skip: continue}`. The node then has no output, and details are
    recorded in memory. A choice is an outcome, not a failure, so it is never
    retried; any other exception fails the node, on the error choice.
    """

    def __init__(self, choice: str, details: Any = None):
        super().__init__(choice, details)
        self.choice = choice
        self.details = details


# A reference in a node's params: ${params.name} for a setting of the
# pipeline, ${inputs.name} for an input of the run, or ${nodes.name.output}
# for the output of a node that ran before.
_REFERENCE = re.compile(r"^\$\{(?:(params|inputs)\.(\w+)|(nodes)\.(\w+)\.output)\}$")


class FnIO:
    """
    How a node function is called: fn(state, **params), with exactly its
    node's params and nothing else. Each is a literal value, ${params.name}
    for a setting of the pipeline, ${inputs.name} for an input of the run,
    or ${nodes.name.output} for the output of a node that ran before. A
    parameter the node doesn't give, and that has no default, is an error
    when the pipeline is built, and so is a reference whose format doesn't
    match the parameter's annotation. The return annotation is the output
    format.

    The function gets the state as a StateView, limited to the capabilities
    of its node.
    """

    def __init__(
        self,
        fn: NodeFn,
        node: "Node",
        builder: "Builder",
        params: dict[str, Any] | None = None,
        provided: tuple[str, ...] = (),
        own: bool = False,
    ):
        """params are the ones fn is called with, the node's by default, and
        provided the ones its node passes when it calls it, e.g. a parallel
        node's results to its join. own is for a node's own run(), which
        gets the state itself rather than a view of it."""
        self.fn = fn
        self.granted = node.granted
        self._own = own
        given = node.params if params is None else params
        try:
            hints = get_type_hints(fn)
        except Exception:
            hints = {}
        try:
            parameters = list(inspect.signature(fn).parameters.values())[1:]
        except (TypeError, ValueError):
            parameters = []
        self.output_type = hints.get("return", Any)

        takes_any = any(p.kind == p.VAR_KEYWORD for p in parameters)
        # The params the function takes by name, None if it takes any.
        self.param_names: set[str] | None = (
            None
            if takes_any
            else {
                p.name
                for p in parameters
                if p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
            }
        )
        for p in parameters:
            missing = (
                p.kind not in (p.VAR_POSITIONAL, p.VAR_KEYWORD)
                and p.default is p.empty
                and p.name not in given
                and p.name not in provided
            )
            if missing:
                taker = (
                    f"Node {node.name}"
                    if own
                    else f"Node {node.name} function {_name(fn)}"
                )
                raise ValueError(
                    f"{taker} takes {p.name!r}, which the node doesn't give in "
                    "its params"
                )
        names = (
            given
            if takes_any
            else {k: v for k, v in given.items() if k in self.param_names}
        )
        # The params resolved now, checked against the function's
        # annotations, and the inputs and outputs read and checked when it's
        # called.
        self._node = node.name
        self._hints = hints
        self._params: dict[str, Any] = {}
        self._reads: dict[str, tuple[str, str]] = {}
        for name, ref in names.items():
            where = f"Node {node.name} param {name}"
            source, key = reference(where, ref)
            if source is None:
                self._params[name] = self._check(name, ref)
            elif source == "params":
                if key not in builder.params:
                    raise ValueError(
                        f"{where} is ${{params.{key}}}, which is not a param "
                        "of the pipeline"
                    )
                self._params[name] = self._check(name, builder.params[key])
            elif source == "inputs":
                if key not in builder.inputs:
                    raise ValueError(
                        f"{where} is ${{inputs.{key}}}, which is not an input "
                        "of the pipeline"
                    )
                self._reads[name] = (source, key)
            else:
                fmt = builder.output_of(where, key)
                hint = hints.get(name, Any)
                if not compatible(fmt, hint):
                    raise ValueError(
                        f"{where} takes {describe(hint)}, but "
                        f"${{nodes.{key}.output}} is {describe(fmt)}"
                    )
                self._reads[name] = (source, key)
        node._fns_io.append(self)

    def _check(self, name: str, value: Any) -> Any:
        """A param's value, checked against its annotation, and coerced if
        needed, e.g. an int for a float."""
        try:
            return check_value(value, self._hints.get(name, Any))
        except TypeError as e:
            raise ValueError(f"Node {self._node} param {name}: {e}") from None

    def _read(self, name: str, source: str, key: str) -> Any:
        if source == "inputs":
            return self._check(name, current_inputs()[key])
        return self._check(name, read_output(self._node, key))

    async def __call__(self, state: State, **provided: Any) -> Any:
        view = state if self._own else StateView(state, self.granted)
        params = {
            **self._params,
            **{n: self._read(n, *source) for n, source in self._reads.items()},
            **provided,
        }
        return await call(self.fn, view, **params)


def read_output(node: str, key: str) -> Any:
    """The output of node key, which node references."""
    outputs = current_outputs()
    if key not in outputs:
        raise RuntimeError(
            f"Node {node} reads ${{nodes.{key}.output}}, but {key} has no output: "
            "it made a choice without one"
        )
    return outputs[key]


def reference(where: str, value: Any) -> tuple[str | None, str | None]:
    """The source, params, inputs or nodes, and the name a value references,
    as in ${params.name}, or (None, None) for a literal."""
    if not isinstance(value, str) or not value.startswith("${"):
        return None, None
    match = _REFERENCE.match(value)
    if match is None:
        raise ValueError(
            f"{where} is {value!r}, but a reference is ${{params.name}}, "
            "${inputs.name} or ${nodes.name.output}"
        )
    return (
        (match.group(1), match.group(2))
        if match.group(1)
        else ("nodes", match.group(4))
    )


def _name(fn: Any) -> str:
    return getattr(fn, "__name__", repr(fn))


_UNITS = {"s": 1, "m": 60, "h": 3600}


def _seconds(v: Any) -> Any:
    """A duration in seconds, from a number or a string like 30s, 10m or 2h."""
    if isinstance(v, str):
        number, unit = v.strip()[:-1], v.strip()[-1:]
        if unit not in _UNITS:
            raise ValueError(
                f"A duration is a number of seconds or like 30s, 10m, 2h, got {v!r}"
            )
        return float(number) * _UNITS[unit]
    return v


Seconds = Annotated[float | None, BeforeValidator(_seconds)]


def _choice_keys(v: Any) -> Any:
    # YAML parses `true:` keys as bools, map them to the condition choices.
    if isinstance(v, dict):
        return {
            (("true" if k else "false") if isinstance(k, bool) else k): t
            for k, t in v.items()
        }
    return v


def _parse_nodes(value: Any, info: ValidationInfo) -> Any:
    """Parse each node dict into the class of its type, so every type only
    accepts its own fields."""
    if not isinstance(value, list):
        return value
    from alphatrion.swarm.nodes import BUILTIN_TYPES

    types = {**BUILTIN_TYPES, **(info.context or {}).get("node_types", {})}
    nodes = []
    for item in value:
        if not isinstance(item, dict):
            nodes.append(item)
            continue
        spec = dict(item)
        # A node with nodes or a subgraph file but no type is a subgraph, so
        # it's written like a pipeline file: a name and its nodes.
        if "type" not in spec and ("nodes" in spec or "subgraph" in spec):
            spec["type"] = "subgraph"
        node_cls = types.get(spec.get("type"))
        if node_cls is None:
            raise ValueError(
                f"Unknown type {spec.get('type')!r} of node {spec.get('name')}, "
                f"expected one of {sorted(types)} or a type passed to "
                "build_graph(node_types=...)"
            )
        nodes.append(node_cls.model_validate(spec, context=info.context))
    return nodes


NodeList = Annotated[list["Node"], BeforeValidator(_parse_nodes)]


class Node(BaseModel):
    """
    The base of graph nodes. A node is both its definition, the fields read
    from YAML or passed in code, and its behavior, run().

    Each node type subclasses it with a `type` literal, its own fields, and
    run(). Nodes that reference functions by name, or nest other nodes,
    resolve them in prepare(), which the graph calls before running.
    Custom types subclass it too, and are passed to build_graph().
    """

    model_config = ConfigDict(extra="forbid")

    # The choices the node can take, only to check its exit and branches keys
    # when a pipeline is built. None means any choice, for nodes whose
    # functions choose it, e.g. by returning a NodeResult.
    choices: ClassVar[frozenset[str] | None] = None
    # Nodes that judge the artifact are never improved, so the system can't
    # change what counts as an improvement.
    ALWAYS_IMMUTABLE: ClassVar[bool] = False
    # The most capabilities a node of this type can have.
    CAPABILITIES: ClassVar[frozenset[Capability]] = frozenset()

    name: str
    type: str
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="What the node's functions get, by parameter name, and all "
        "they get besides the value: a literal, ${params.name} for a setting "
        "of the pipeline, or ${inputs.name} for an input of the run.",
    )
    exit: str | dict[str, str] | None = Field(
        default=None,
        description="An exit to take after this node: end, or in a loop, continue "
        "to start the next iteration and break to end the loop. Either one exit, "
        "or a map from the node chooses exits, with an optional default key. "
        "Choices without an exit or a branch fall through to the next node.",
    )
    branches: dict[str, NodeList] = Field(
        default_factory=dict,
        description="The nodes to run for each choice of this node. A branch "
        "continues with the node after this one when it is done.",
    )
    mutable: bool = Field(
        default=False,
        description="Whether self-improvement may change the node. An immutable "
        "node stays as written, its nested nodes included, which "
        "check_mutation() enforces. Evaluators and guardrails are always "
        "immutable.",
    )
    timeout: Seconds = Field(
        default=None,
        gt=0,
        description="The most a node may run, e.g. 60s or 10m, every function "
        "and nested node included. On expiry the engine cancels it and stops "
        "its runtime, and it fails on the timeout choice. None for no limit.",
    )
    retries: int = Field(
        default=0,
        ge=0,
        description="How many times to run the node again after it fails, by "
        "raising or timing out, each time from where it started. A choice it "
        "makes, e.g. a guardrail's fail, is an outcome, never retried.",
    )
    runtime: str | None = Field(
        default=None,
        description="The name of a runtime in the pipeline's runtimes, which "
        "the node runs in: a fresh one for each attempt, stopped when it ends. "
        "Its functions reach it as state.runtime. None to run in the engine's "
        "process.",
    )
    capabilities: list[Capability] | None = Field(
        default=None,
        description="What the node may do beyond reading the state, e.g. "
        "commit artifacts. None grants all its type can have, and a list "
        "narrows them; it can't add any. Self-improvement can only narrow the "
        "capabilities of a mutable node, never add to them.",
    )

    _prepared: bool = PrivateAttr(default=False)
    # The functions of the node, registered as they are resolved.
    _fns_io: list[FnIO] = PrivateAttr(default_factory=list)
    # The node's own run(), if it takes params.
    _run_io: FnIO | None = PrivateAttr(default=None)
    # The node's runtime, resolved from the pipeline's runtimes.
    _runtime: "RuntimePlan | None" = PrivateAttr(default=None)

    @field_validator("exit", "branches", mode="before")
    @classmethod
    def bool_choices(cls, v: Any) -> Any:
        return _choice_keys(v)

    @field_validator("mutable")
    @classmethod
    def judges_are_immutable(cls, v: bool) -> bool:
        if v and cls.ALWAYS_IMMUTABLE:
            raise ValueError(
                f"A {cls.node_type()} node is always immutable, since it "
                "judges what counts as an improvement"
            )
        return v

    @field_validator("capabilities")
    @classmethod
    def within_type(cls, v: list[Capability] | None) -> list[Capability] | None:
        extra = set(v or []) - cls.CAPABILITIES
        if extra:
            allowed = ", ".join(sorted(cls.CAPABILITIES)) or "none"
            raise ValueError(
                f"A {cls.node_type()} node can't have {', '.join(sorted(extra))}, "
                f"its capabilities are: {allowed}"
            )
        return v

    @property
    def granted(self) -> frozenset[Capability]:
        """The capabilities the node has."""
        if self.capabilities is None:
            return self.CAPABILITIES
        return frozenset(self.capabilities)

    @classmethod
    def node_type(cls) -> str:
        return cls.model_fields["type"].default

    @property
    def prepared(self) -> bool:
        return self._prepared

    def prepare(self, builder: "Builder") -> None:
        """Resolve function references and build nested graphs with the
        builder. Subclasses that need it override _prepare()."""
        if self.runtime is not None:
            self._runtime = builder.runtime(self.name, self.runtime)
        self._prepare(builder)
        if len(inspect.signature(self.run).parameters) > 1:
            self._run_io = FnIO(self.run, self, builder, own=True)
        # A param none of the node's functions takes is a mistake, e.g. a
        # misspelled name.
        if self._fns_io and all(f.param_names is not None for f in self._fns_io):
            taken = set().union(*(f.param_names for f in self._fns_io))
            unused = set(self.params) - taken
            if unused:
                raise ValueError(
                    f"Node {self.name} has params it doesn't take: "
                    f"{', '.join(sorted(unused))}"
                )
        self._prepared = True

    def _prepare(self, builder: "Builder") -> None:
        pass

    @property
    def required_choices(self) -> set[str]:
        """Choices that must have an outgoing edge, checked by the graph."""
        return set()

    def output_type(self) -> Any:
        """The format of the node's output, which later nodes reference as
        ${nodes.name.output}, Any if unknown, None if it has none, like a
        decision."""
        return Any

    def outputs_on(self, choice: str | None) -> bool:
        """Whether the node has an output after the choice: for most nodes,
        only with None, no choice, its normal path."""
        return choice is None

    @abstractmethod
    async def run(self, state: State) -> NodeResult:
        """Run the node. The output of the result, with a choice the node
        outputs on, is what later nodes reference.

        A node that takes something declares it as parameters of run, with
        type hints, e.g. run(self, state, request: ModelRequest): its params
        are then run's, resolved and checked like a function's, and passed
        to it. Otherwise its params are its functions'."""

    async def call(self, state: State) -> NodeResult:
        """Run the node, with its params if run takes them."""
        if self._run_io is not None:
            return await self._run_io(state)
        return await self.run(state)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(name={self.name!r})"
