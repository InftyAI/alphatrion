from abc import abstractmethod
from typing import Any

from alphatrion.swarm.nodes.base import Node, NodeResult
from alphatrion.swarm.state import State


class DecisionNode(Node):
    """
    The base of nodes that decide where the pipeline goes next, e.g. a
    condition, a switch or a guardrail. A decision has no output: what was
    decided is recorded in memory as details, and its functions take what
    they decide on by reference, like any node function.

    Subclasses implement decide(). Custom decision nodes subclass it too.
    """

    @abstractmethod
    async def decide(self, state: State) -> tuple[str, Any]:
        """Return the choose take, and the details to record."""

    def output_type(self) -> Any:
        return None

    def outputs_on(self, choice: str | None) -> bool:
        return False

    async def run(self, state: State) -> NodeResult:
        choice, details = await self.decide(state)
        return NodeResult(choice=choice, details=details)
