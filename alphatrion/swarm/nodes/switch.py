from typing import TYPE_CHECKING, Any, Literal, Self

from pydantic import Field, PrivateAttr, model_validator

from alphatrion.swarm.nodes.base import FnIO, FnRef
from alphatrion.swarm.nodes.decision import DecisionNode
from alphatrion.swarm.state import State

if TYPE_CHECKING:
    from alphatrion.swarm.pipeline import Builder


class SwitchNode(DecisionNode):
    """
    Chooses by fn(state, **params), which returns the name of a case,
    e.g. to pick which job to run next. The cases are the keys of the node's
    branches and exit. A case without a key fails the node, unless a
    `default` key catches every other case.
    """

    type: Literal["switch"] = "switch"
    fn: FnRef = Field(description="Returns a case, resolved like an action fn.")

    _fn: FnIO = PrivateAttr()

    @model_validator(mode="after")
    def has_cases(self) -> Self:
        if not self.cases and not self.has_default:
            raise ValueError(f"Switch {self.name} requires cases in branches or exit")
        return self

    @property
    def cases(self) -> set[str]:
        keys = set(self.branches)
        if isinstance(self.exit, dict):
            keys |= set(self.exit)
        return keys - {"default"}

    @property
    def has_default(self) -> bool:
        return isinstance(self.exit, str) or (
            isinstance(self.exit, dict) and "default" in self.exit
        )

    def _prepare(self, builder: "Builder") -> None:
        self._fn = FnIO(builder.resolve(self.fn), self, builder)

    async def decide(self, state: State) -> tuple[str, Any]:
        case = await self._fn(state)
        if not isinstance(case, str):
            raise TypeError(
                f"Switch {self.name} must return a str, got {type(case).__name__}"
            )
        if case not in self.cases and not self.has_default:
            raise ValueError(
                f"Switch {self.name} returned {case!r}, which has no case, "
                f"expected one of {sorted(self.cases)}"
            )
        return case, case
