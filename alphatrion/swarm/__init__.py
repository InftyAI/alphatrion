"""The recursive self-improvement system, built on `alphatrion.framework`.

Install with `pip install alphatrion[all]`.
"""

from alphatrion.swarm.capabilities import Capability, CapabilityError, StateView
from alphatrion.swarm.formats import (
    Execution,
    Files,
    Format,
    Metrics,
    ModelRequest,
    ModelResponse,
    Text,
)
from alphatrion.swarm.graph import (
    BREAK,
    CONTINUE,
    END,
    RAISE,
    ChoiceError,
    Edge,
    Graph,
    GraphResult,
    GraphStatus,
)
from alphatrion.swarm.memory import Memory, MemoryEntry
from alphatrion.swarm.nodes import (
    ActionNode,
    Choice,
    ConditionNode,
    DecisionNode,
    EvaluatorNode,
    GuardrailNode,
    LoopNode,
    ModelRouterNode,
    Node,
    NodeResult,
    ParallelNode,
    SubgraphNode,
    SwitchNode,
)
from alphatrion.swarm.pipeline import (
    Pipeline,
    build_graph,
    check_mutation,
    load_pipeline,
)
from alphatrion.swarm.requests import RequestRecord, Requests
from alphatrion.swarm.state import State
from alphatrion.swarm.store import HostStore, RunStore
from alphatrion.swarm.tree import Artifact, ScoreMode, Tree

__all__ = [
    "Capability",
    "CapabilityError",
    "StateView",
    "Execution",
    "Files",
    "Format",
    "Metrics",
    "ModelRequest",
    "ModelResponse",
    "Text",
    "BREAK",
    "RAISE",
    "CONTINUE",
    "END",
    "ActionNode",
    "Artifact",
    "Tree",
    "ConditionNode",
    "DecisionNode",
    "Edge",
    "EvaluatorNode",
    "GuardrailNode",
    "LoopNode",
    "ModelRouterNode",
    "Memory",
    "MemoryEntry",
    "Node",
    "NodeResult",
    "Choice",
    "ParallelNode",
    "ChoiceError",
    "ScoreMode",
    "State",
    "HostStore",
    "RunStore",
    "RequestRecord",
    "Requests",
    "SwitchNode",
    "Pipeline",
    "Graph",
    "SubgraphNode",
    "GraphResult",
    "GraphStatus",
    "build_graph",
    "check_mutation",
    "load_pipeline",
]
