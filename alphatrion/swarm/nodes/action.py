from typing import TYPE_CHECKING, Any, ClassVar, Literal

from pydantic import Field, PrivateAttr

from alphatrion.swarm.capabilities import Capability
from alphatrion.swarm.nodes.base import FnIO, FnRef, Node, NodeResult
from alphatrion.swarm.state import State

if TYPE_CHECKING:
    from alphatrion.swarm.pipeline import Builder


class ActionNode(Node):
    """
    Runs fn(state, **params), e.g. to build a model request or apply a
    model's edit. Its return value is its output, which later nodes
    reference as ${nodes.name.output}, and its return annotation is the
    output format.

    fn can also raise Choice to make a choice rather than output, e.g.
    raise Choice("skip", reason) for an exit like `exit: {skip: continue}`.
    """

    CAPABILITIES: ClassVar[frozenset[Capability]] = frozenset(
        {Capability.COMMIT, Capability.REMEMBER}
    )

    type: Literal["action"] = "action"
    fn: FnRef = Field(
        description="The node function, either a name registered in the functions "
        "passed to build_graph(), an import path like 'package.module:func', "
        "or the function itself."
    )

    _fn: FnIO = PrivateAttr()

    def _prepare(self, builder: "Builder") -> None:
        self._fn = FnIO(builder.resolve(self.fn), self, builder)

    def output_type(self) -> Any:
        return self._fn.output_type

    async def run(self, state: State) -> NodeResult:
        return NodeResult(output=await self._fn(state))
