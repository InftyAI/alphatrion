from typing import TYPE_CHECKING, Any, ClassVar, Literal

from pydantic import Field, PrivateAttr

from alphatrion.swarm.context import current_store, in_iteration
from alphatrion.swarm.nodes.base import (
    NO_OUTPUT,
    FnIO,
    FnRef,
    Node,
    NodeList,
    NodeResult,
)
from alphatrion.swarm.state import State

if TYPE_CHECKING:
    from alphatrion.swarm.graph import Graph
    from alphatrion.swarm.pipeline import Builder


class LoopNode(Node):
    """
    Runs its nodes repeatedly, e.g. an agent exploring improvements. Each
    iteration's nodes reference the outputs before the loop and their own,
    not a previous iteration's: what carries over is in the tree and the
    memory. A `continue` exit discards the iteration.

    The loop ends at a `break` exit, when until(state, **params) returns
    true after an iteration, or after max_iters iterations. With
    max_iters=None and no until, it loops until its task is cancelled. An
    `end` exit inside ends the run the loop is in. Its output is the last
    output of the last iteration that wasn't discarded.

    It chooses "completed" when ended by break or until, and to
    "max_iters" when it runs out of iterations. A failed iteration, e.g.
    one that took a `raise` exit, fails this node too.
    """

    COMPLETED: ClassVar[str] = "completed"
    MAX_ITERS: ClassVar[str] = "max_iters"
    choices: ClassVar[frozenset[str] | None] = frozenset({COMPLETED, MAX_ITERS})

    type: Literal["loop"] = "loop"
    nodes: NodeList = Field(min_length=1, description="The body of the loop.")
    max_iters: int | None = Field(
        default=None, ge=1, description="The maximum iterations, unlimited if None."
    )
    until: FnRef | None = Field(
        default=None,
        description="Ends the loop when it returns true after an iteration, "
        "resolved like an action fn, with the loop's params.",
    )

    _graph: "Graph" = PrivateAttr()
    _until: FnIO | None = PrivateAttr(default=None)

    def _prepare(self, builder: "Builder") -> None:
        from alphatrion.swarm.graph import BREAK, CONTINUE, NEXT

        self._graph = builder.graph(
            self.name, self.nodes, exits={CONTINUE, BREAK, NEXT}, after=NEXT
        )
        if self.until is not None:
            self._until = FnIO(builder.resolve(self.until), self, builder)

    def output_type(self) -> Any:
        return self._graph.output_type

    def outputs_on(self, choice: str | None) -> bool:
        return True

    async def run(self, state: State) -> NodeResult:
        from alphatrion.swarm.graph import BREAK, CONTINUE, END, GraphStatus

        iterations = 0
        output = NO_OUTPUT
        while self.max_iters is None or iterations < self.max_iters:
            with in_iteration(state.node or self.name, iterations + 1):
                result = await self._graph.run(state=state)
            iterations += 1
            store = current_store()
            if store is not None:
                store.iteration(state, state.node or self.name, iterations)
            if result.status == GraphStatus.FAILED:
                raise RuntimeError(
                    f"Loop {self.name} failed at iteration {iterations}: {result.error}"
                )
            details = {"iterations": iterations}
            # A continue discards the iteration, e.g. to drop a candidate
            # that didn't improve.
            if result.exit != CONTINUE:
                output = result.output
            if result.exit in (END, BREAK):
                return NodeResult(
                    choice=self.COMPLETED,
                    output=output,
                    details=details,
                    exit=END if result.exit == END else None,
                )
            if self._until is not None and await self._until(state):
                return NodeResult(choice=self.COMPLETED, output=output, details=details)
        return NodeResult(
            choice=self.MAX_ITERS, output=output, details={"iterations": iterations}
        )
