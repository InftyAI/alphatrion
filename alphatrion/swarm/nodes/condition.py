from typing import TYPE_CHECKING, Any, ClassVar, Literal

from pydantic import Field, PrivateAttr

from alphatrion.swarm.nodes.base import FnIO, FnRef
from alphatrion.swarm.nodes.decision import DecisionNode
from alphatrion.swarm.state import State

if TYPE_CHECKING:
    from alphatrion.swarm.pipeline import Builder


class ConditionNode(DecisionNode):
    """
    Chooses by fn(state, **params), which returns a bool: True chooses
    "true" and False "false". To choose among more options, use a switch.
    """

    choices: ClassVar[frozenset[str] | None] = frozenset({"true", "false"})

    type: Literal["condition"] = "condition"
    fn: FnRef = Field(description="Returns a bool, resolved like an action fn.")

    _fn: FnIO = PrivateAttr()

    def _prepare(self, builder: "Builder") -> None:
        self._fn = FnIO(builder.resolve(self.fn), self, builder)

    async def decide(self, state: State) -> tuple[str, Any]:
        result = await self._fn(state)
        if not isinstance(result, bool):
            raise TypeError(
                f"Condition {self.name} must return a bool, got {type(result).__name__}"
            )
        return ("true" if result else "false"), result
