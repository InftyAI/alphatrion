import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Self, get_type_hints

from pydantic import Field, PrivateAttr, model_validator

from alphatrion.swarm.capabilities import Capability
from alphatrion.swarm.nodes.base import (
    FnIO,
    FnRef,
    Node,
    NodeList,
    NodeResult,
)
from alphatrion.swarm.state import State

if TYPE_CHECKING:
    from alphatrion.swarm.graph import Graph, GraphResult
    from alphatrion.swarm.pipeline import Builder

# A join takes the parent state, the results of the finished branches in
# branch order, and the node params. It can raise Choice to make a choice.
JoinFn = Callable[..., Any]


def join_best(state: State, results: list["GraphResult"]) -> Any:
    """Make the best scored artifact among the branches current, and output
    the output of the branch that produced it."""
    scored = [
        r
        for r in results
        if r.state.current is not None and r.state.current.score is not None
    ]
    if not scored:
        raise RuntimeError("No branch ended with a scored artifact")
    # max() keeps the first on a tie, i.e. the lowest branch index.
    best = max(scored, key=lambda r: r.state.current.score)
    state.checkout(best.state.current_id)
    return best.output


def join_all(state: State, results: list["GraphResult"]) -> list[Any]:
    """Output the outputs of every branch, in branch order, without moving
    the parent's current artifact."""
    return [r.output for r in results]


JOINS: dict[str, JoinFn] = {"best": join_best, "all": join_all}


class ParallelNode(Node):
    """
    Runs its nodes in n concurrent branches, e.g. to explore several
    improvements of the current artifact at once. Each branch runs on a
    fork of the state: it shares the memory and the tree, but evolves its
    own current artifact from the parent's.

    The branches can loop forever, e.g. a loop with max_iters=None, until
    the node is cancelled.

    wait sets when to join: None waits for every branch to finish, and fails
    if any branch failed. An int k joins once k branches have finished,
    ignoring failed ones, and then cancels the rest.

    Each branch is its own run, so an `end` or `raise` exit inside a branch
    only finishes or fails that branch.

    join merges the finished branches: "best", "all", or a JoinFn.
    """

    # The join moves the current artifact to the one it picks.
    CAPABILITIES: ClassVar[frozenset[Capability]] = frozenset({Capability.COMMIT})

    type: Literal["parallel"] = "parallel"
    nodes: NodeList = Field(min_length=1, description="The body of each branch.")
    n: int = Field(ge=1, description="The number of branches.")
    wait: int | None = Field(
        default=None,
        ge=1,
        description="Join once this many branches finished, all branches if None.",
    )
    join: FnRef = Field(
        default="best",
        description="How to merge the branches: best, all, or a function "
        "resolved like an action fn.",
    )

    _graph: "Graph" = PrivateAttr()
    _join: JoinFn = PrivateAttr()
    _join_io: FnIO = PrivateAttr()

    @model_validator(mode="after")
    def wait_within_n(self) -> Self:
        if self.wait is not None and self.wait > self.n:
            raise ValueError(f"Parallel {self.name} requires wait <= n")
        return self

    def output_type(self) -> Any:
        if self._join is join_best:
            return self._graph.output_type
        if self._join is join_all:
            return list[self._graph.output_type]
        try:
            return get_type_hints(self._join).get("return", Any)
        except Exception:
            return Any

    def _prepare(self, builder: "Builder") -> None:
        from alphatrion.swarm.graph import DONE

        self._graph = builder.graph(self.name, self.nodes, exits={DONE}, after=DONE)
        if isinstance(self.join, str) and self.join in JOINS:
            self._join = JOINS[self.join]
        else:
            self._join = builder.resolve(self.join)
        self._join_io = FnIO(self._join, self, builder, provided=("results",))

    async def run(self, state: State) -> NodeResult:
        from alphatrion.swarm.graph import GraphStatus

        async def branch(i: int) -> tuple[int, "GraphResult"]:
            branch_state = state.fork(f"{self.name}[{i}]")
            return i, await self._graph.run(state=branch_state)

        need = self.n if self.wait is None else self.wait
        tasks = [asyncio.create_task(branch(i)) for i in range(self.n)]
        finished: list[tuple[int, GraphResult]] = []
        failures: list[str] = []
        try:
            for next_done in asyncio.as_completed(tasks):
                i, result = await next_done
                if result.status == GraphStatus.COMPLETED:
                    finished.append((i, result))
                    if len(finished) >= need:
                        break
                    continue

                # A failed branch never stops the others: each branch is its
                # own run, and only this node decides when to stop them.
                failures.append(f"branch {i} {result.status.value}: {result.error}")
        finally:
            # Cancel the branches still running, e.g. once enough have finished
            # or when this node is cancelled, and wait for them to unwind.
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        if len(finished) < need:
            raise RuntimeError(
                f"Parallel {self.name} needs {need} finished branches, "
                f"got {len(finished)}: {'; '.join(failures)}"
            )

        results = [r for _, r in sorted(finished, key=lambda x: x[0])]
        return NodeResult(output=await self._join_io(state, results=results))
