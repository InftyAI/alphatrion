from typing import TYPE_CHECKING, Any, ClassVar, Literal, Self

from pydantic import Field, PrivateAttr, model_validator

from alphatrion.swarm.nodes.base import Node, NodeList, NodeResult
from alphatrion.swarm.state import State

if TYPE_CHECKING:
    from alphatrion.swarm.graph import Graph
    from alphatrion.swarm.pipeline import Builder


class SubgraphNode(Node):
    """
    Runs a subgraph as one node, e.g. the steps of an experiment as one step
    of a research loop. Its nodes are either inline, or in a pipeline file,
    relative to the pipeline that references it, so a subgraph can be
    reused across pipelines. Its type can be left out: a node with nodes or
    a subgraph file and no type is a subgraph.

    It behaves like a function call: its nodes reference the outputs before
    it, and its output is the last output of its nodes. An `end` exit inside
    returns to the parent, and loops' `continue` and `break` don't cross it.
    Its nodes have a name scope of their own, and are recorded in memory as
    <subgraph>.<name>.
    """

    choices: ClassVar[frozenset[str] | None] = frozenset()

    type: Literal["subgraph"] = "subgraph"
    nodes: NodeList | None = Field(default=None, description="The inline nodes.")
    subgraph: str | None = Field(
        default=None,
        description="A pipeline file with the nodes, relative to the pipeline "
        "referencing it.",
    )

    _graph: "Graph" = PrivateAttr()

    @model_validator(mode="after")
    def nodes_or_pipeline(self) -> Self:
        if (self.nodes is None) == (self.subgraph is None):
            raise ValueError(f"Subgraph {self.name} requires either nodes or subgraph")
        return self

    def _prepare(self, builder: "Builder") -> None:
        self._graph = builder.subgraph(self.name, self.nodes, self.subgraph)

    def output_type(self) -> Any:
        return self._graph.output_type

    async def run(self, state: State) -> NodeResult:
        from alphatrion.swarm.graph import GraphStatus

        result = await self._graph.run(state=state)
        if result.status == GraphStatus.FAILED:
            raise RuntimeError(f"Subgraph {self.name} failed: {result.error}")
        return NodeResult(output=result.output)
