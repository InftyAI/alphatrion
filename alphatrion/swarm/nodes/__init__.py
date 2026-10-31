from alphatrion.swarm.nodes.action import ActionNode
from alphatrion.swarm.nodes.base import (
    Choice,
    FnRef,
    Node,
    NodeFn,
    NodeList,
    NodeResult,
)
from alphatrion.swarm.nodes.condition import ConditionNode
from alphatrion.swarm.nodes.decision import DecisionNode
from alphatrion.swarm.nodes.evaluator import EvaluatorNode
from alphatrion.swarm.nodes.guardrail import GuardrailNode
from alphatrion.swarm.nodes.loop import LoopNode
from alphatrion.swarm.nodes.model_router import Candidate, ModelRouterNode
from alphatrion.swarm.nodes.parallel import JOINS, JoinFn, ParallelNode
from alphatrion.swarm.nodes.subgraph import SubgraphNode
from alphatrion.swarm.nodes.switch import SwitchNode

# The built-in node types, by type.
BUILTIN_TYPES: dict[str, type[Node]] = {
    node.node_type(): node
    for node in (
        ActionNode,
        ConditionNode,
        EvaluatorNode,
        SubgraphNode,
        GuardrailNode,
        LoopNode,
        ModelRouterNode,
        ParallelNode,
        SwitchNode,
    )
}

__all__ = [
    "BUILTIN_TYPES",
    "JOINS",
    "ActionNode",
    "ConditionNode",
    "DecisionNode",
    "EvaluatorNode",
    "FnRef",
    "SubgraphNode",
    "GuardrailNode",
    "JoinFn",
    "Candidate",
    "LoopNode",
    "ModelRouterNode",
    "Node",
    "NodeFn",
    "NodeList",
    "NodeResult",
    "Choice",
    "ParallelNode",
    "SwitchNode",
]
