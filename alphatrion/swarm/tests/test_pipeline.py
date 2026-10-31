from typing import Any, Literal

import pytest

from alphatrion.swarm import (
    ActionNode,
    ConditionNode,
    EvaluatorNode,
    GraphStatus,
    GuardrailNode,
    LoopNode,
    Node,
    NodeResult,
    ParallelNode,
    State,
    build_graph,
)
from alphatrion.swarm.pipeline import Pipeline

# An improvement loop.
LOOP_PIPELINE = """
name: rsi
nodes:
  - name: improve
    type: loop
    max_iters: 10
    until: good_enough
    params: {target: 3}
    nodes:
      - {name: propose, type: action, fn: propose}
      - name: guard
        type: guardrail
        checks: [not_negative]
        exit: {fail: continue}
      - {name: evaluate, type: evaluator, fn: score}
"""

# Parallel explorers, each a loop, then a report.
EXPLORE_PIPELINE = """
name: explore
nodes:
  - {name: seed, type: action, fn: seed}
  - name: explore
    type: parallel
    n: 3
    join: best
    nodes:
      - name: explorer
        type: loop
        until: found_better
        nodes:
          - {name: propose, type: action, fn: propose_variant}
          - {name: evaluate, type: evaluator, fn: score}
          - name: check
            type: condition
            fn: improved
            exit: {true: break, false: continue}
  - {name: report, type: action, fn: report}
"""


def functions():
    from alphatrion.swarm.tests import test_graph as t

    return {
        "propose": t.propose,
        "not_negative": t.not_negative,
        "score": t.score,
        "good_enough": t.good_enough,
    }


@pytest.mark.asyncio
async def test_improvement_loop(tmp_path):
    path = tmp_path / "pipeline.yaml"
    path.write_text(LOOP_PIPELINE)
    graph = build_graph(path, functions=functions())

    assert graph.name == "rsi"
    result = await graph.run()
    assert result.status == GraphStatus.COMPLETED
    assert result.state.tree.best().score == 3


@pytest.mark.asyncio
async def test_pipeline_in_code():
    # The same pipeline as LOOP_PIPELINE, with the functions passed directly.
    t = functions()
    pipeline = Pipeline(
        name="rsi",
        nodes=[
            LoopNode(
                name="improve",
                max_iters=10,
                until=t["good_enough"],
                params={"target": 3},
                nodes=[
                    ActionNode(name="propose", fn=t["propose"]),
                    GuardrailNode(
                        name="guard",
                        checks=[t["not_negative"]],
                        exit={"fail": "continue"},
                    ),
                    EvaluatorNode(name="evaluate", fn=t["score"]),
                ],
            )
        ],
    )
    result = await build_graph(pipeline).run()
    assert result.status == GraphStatus.COMPLETED
    assert result.state.tree.best().score == 3


def test_loop_pipeline_structure():
    graph = build_graph(
        {
            "nodes": [
                {
                    "name": "improve",
                    "type": "loop",
                    "max_iters": 10,
                    "nodes": [{"name": "propose", "type": "action", "fn": "propose"}],
                }
            ]
        },
        functions=functions(),
    )
    loop = graph.nodes["improve"]
    assert isinstance(loop, LoopNode)
    assert loop.max_iters == 10
    assert [node.name for node in loop.nodes] == ["propose"]


@pytest.mark.asyncio
async def test_explore_pipeline(tmp_path):
    path = tmp_path / "pipeline.yaml"
    path.write_text(EXPLORE_PIPELINE)
    reports = []

    def propose_variant(state: State):
        # Each explorer improves its own lineage by one per iteration.
        return state.commit(state.current.content + 1)

    def improved(state: State):
        return state.current.score >= 2 + int(state.branch[-2])

    graph = build_graph(
        path,
        functions={
            "seed": lambda state: state.commit(0),
            "propose_variant": propose_variant,
            "score": lambda state: state.current.content,
            "improved": improved,
            "found_better": lambda state: False,
            "report": lambda state: reports.append(state.current.score),
        },
    )
    assert isinstance(graph.nodes["explore"], ParallelNode)

    result = await graph.run()
    assert result.status == GraphStatus.COMPLETED
    # Explorer i breaks once it reaches 2 + i, and the best of them is kept.
    assert reports == [4]
    assert len(result.state.tree.children(result.state.tree.root.id)) == 3


BRANCH_PIPELINE = """
name: jobs
nodes:
  - name: work
    type: loop
    max_iters: 4
    nodes:
      # More than two choices: a switch picks one by name.
      - name: pick
        type: switch
        fn: pick
        branches:
          generate:
            - {name: propose, type: action, fn: log}
            - name: guard
              type: guardrail
              checks: [ok]
              exit: {fail: continue}
            - {name: register, type: action, fn: log}
          ablate:
            - {name: ablate, type: action, fn: log}
            - {name: stop, type: condition, fn: stop, exit: {true: break}}
          # An empty case does nothing and continues with the next node.
          idle: []
      - {name: after, type: action, fn: log}
  - {name: report, type: action, fn: log}
"""


@pytest.mark.asyncio
async def test_branches(tmp_path):
    path = tmp_path / "pipeline.yaml"
    path.write_text(BRANCH_PIPELINE)
    log = []
    picks = iter(["generate", "generate", "idle", "ablate"])
    guard_results = iter([True, False])

    def log_node(state: State):
        log.append(state.node)

    graph = build_graph(
        path,
        functions={
            "pick": lambda state: next(picks),
            "log": log_node,
            "ok": lambda state: next(guard_results),
            "stop": lambda state: True,
        },
    )
    result = await graph.run()

    assert result.status == GraphStatus.COMPLETED
    assert log == [
        # A branch continues with the node after its deciding node.
        "propose",
        "register",
        "after",
        # The guard fails and continues to the next iteration.
        "propose",
        # An empty case continues with the next node.
        "after",
        # Break ends the loop from inside a branch.
        "ablate",
        "report",
    ]


def test_branches_in_code():
    graph = build_graph(
        Pipeline(
            nodes=[
                ConditionNode(
                    name="check",
                    fn=lambda state: True,
                    branches={"true": [ActionNode(name="yes", fn=lambda state: None)]},
                    exit={"false": "end"},
                ),
                ActionNode(name="done", fn=lambda state: None),
            ]
        )
    )
    edges = {(e.source, e.target, e.when) for e in graph.edges}
    assert edges == {
        ("check", "yes", "true"),
        ("check", "end", "false"),
        ("check", "done", None),
        ("yes", "done", None),
        ("done", "end", None),
    }
    assert graph.entry == "check"


class LLMNode(Node):
    """A custom node type: its own fields, and what it does."""

    type: Literal["llm"] = "llm"
    model: str

    def output_type(self) -> Any:
        return str

    async def run(self, state: State) -> NodeResult:
        return NodeResult(output=self.model)


class ShoutNode(Node):
    """A custom node taking a param: it declares it in run, and gets it
    resolved and checked, like a function's."""

    type: Literal["shout"] = "shout"

    def output_type(self) -> Any:
        return str

    async def run(self, state: State, text: str) -> NodeResult:
        return NodeResult(output=text.upper())


@pytest.mark.asyncio
async def test_custom_type_with_params():
    pipeline = {
        "nodes": [
            {"name": "ask", "type": "llm", "model": "claude-opus-5-5"},
            {
                "name": "shout",
                "type": "shout",
                "params": {"text": "${nodes.ask.output}"},
            },
        ]
    }
    result = await build_graph(pipeline, node_types=[LLMNode, ShoutNode]).run()
    assert result.status == GraphStatus.COMPLETED, result.error
    assert result.output == "CLAUDE-OPUS-5-5"
    with pytest.raises(ValueError, match="Node shout takes 'text'"):
        build_graph(
            {"nodes": [{"name": "shout", "type": "shout"}]}, node_types=[ShoutNode]
        )


@pytest.mark.asyncio
async def test_custom_type(tmp_path):
    path = tmp_path / "pipeline.yaml"
    path.write_text("nodes:\n  - {name: ask, type: llm, model: claude-opus-5-5}\n")
    graph = build_graph(path, node_types=[LLMNode])
    result = await graph.run()
    assert (
        result.state.memory.history(node="ask")[0].data["output"] == "claude-opus-5-5"
    )

    # Custom types are validated like the built-in ones.
    with pytest.raises(ValueError, match="model"):
        build_graph({"nodes": [{"name": "ask", "type": "llm"}]}, node_types=[LLMNode])
    # And they are unknown unless passed.
    with pytest.raises(ValueError, match="Unknown type 'llm'"):
        build_graph(path)


@pytest.mark.parametrize(
    "nodes, error",
    [
        ([{"name": "a", "type": "unknown"}], ValueError),
        # exit and branches keys must be choices of the node.
        (
            [
                {
                    "name": "g",
                    "type": "guardrail",
                    "checks": ["builtins:bool"],
                    "exit": {"fial": "end"},
                }
            ],
            ValueError,
        ),
        (
            [
                {
                    "name": "c",
                    "type": "condition",
                    "fn": "builtins:bool",
                    "branches": {
                        "maybe": [
                            {
                                "name": "a",
                                "type": "action",
                                "fn": "builtins:print",
                            }
                        ]
                    },
                }
            ],
            ValueError,
        ),
        (
            [
                {
                    "name": "e",
                    "type": "evaluator",
                    "fn": "builtins:len",
                    "exit": {"true": "end"},
                }
            ],
            ValueError,
        ),
        # Every type only accepts its own fields.
        (
            [
                {
                    "name": "a",
                    "type": "action",
                    "fn": "builtins:print",
                    "max_iters": 5,
                }
            ],
            ValueError,
        ),
        ([{"name": "a", "type": "action"}], ValueError),
        ([{"name": "a", "type": "action", "fn": "unregistered"}], KeyError),
        # A guardrail must say where to go when it fails.
        ([{"name": "a", "type": "guardrail", "checks": ["builtins:bool"]}], ValueError),
        # continue and break only make sense in a loop.
        (
            [
                {
                    "name": "a",
                    "type": "action",
                    "fn": "builtins:print",
                    "exit": "break",
                }
            ],
            ValueError,
        ),
        # exit only takes exits, there is no goto.
        (
            [
                {
                    "name": "a",
                    "type": "action",
                    "fn": "builtins:print",
                    "exit": "x",
                }
            ],
            ValueError,
        ),
        # A choice can't both exit and branch.
        (
            [
                {
                    "name": "a",
                    "type": "condition",
                    "fn": "builtins:bool",
                    "exit": {"true": "end"},
                    "branches": {
                        "true": [
                            {
                                "name": "b",
                                "type": "action",
                                "fn": "builtins:print",
                            }
                        ]
                    },
                }
            ],
            ValueError,
        ),
        # Names are unique, nested nodes included.
        (
            [
                {
                    "name": "a",
                    "type": "condition",
                    "fn": "builtins:bool",
                    "branches": {
                        "true": [
                            {
                                "name": "a",
                                "type": "action",
                                "fn": "builtins:print",
                            }
                        ]
                    },
                }
            ],
            ValueError,
        ),
        # continue only works in a loop, not in a parallel body.
        (
            [
                {
                    "name": "p",
                    "type": "parallel",
                    "n": 2,
                    "nodes": [
                        {
                            "name": "a",
                            "type": "action",
                            "fn": "builtins:print",
                            "exit": "continue",
                        }
                    ],
                }
            ],
            ValueError,
        ),
        ([{"name": "a", "type": "loop", "nodes": []}], ValueError),
        # Repetition is a loop node, exit can't go back.
        (
            [
                {"name": "a", "type": "action", "fn": "builtins:print"},
                {
                    "name": "b",
                    "type": "action",
                    "fn": "builtins:print",
                    "exit": "a",
                },
            ],
            ValueError,
        ),
    ],
)
def test_invalid_pipeline(nodes, error):
    with pytest.raises(error):
        build_graph({"nodes": nodes})


def build_switch(value, exit=None):
    log = []
    switch = {
        "name": "pick",
        "type": "switch",
        "fn": "pick",
        "branches": {"a": [{"name": "on_a", "type": "action", "fn": "log"}]},
    }
    if exit is not None:
        switch["exit"] = exit
    graph = build_graph(
        {"nodes": [switch, {"name": "after", "type": "action", "fn": "log"}]},
        functions={
            "pick": lambda state: value,
            "log": lambda state: log.append(state.node),
        },
    )
    return graph, log


@pytest.mark.asyncio
async def test_switch():
    graph, log = build_switch("a")
    assert (await graph.run()).status == GraphStatus.COMPLETED
    assert log == ["on_a", "after"]

    # A value without a case fails, rather than falling through.
    graph, log = build_switch("b")
    result = await graph.run()
    assert result.status == GraphStatus.FAILED
    assert "returned 'b', which has no case" in result.error

    # Unless default catches every other value.
    graph, log = build_switch("b", exit={"default": "end"})
    assert (await graph.run()).status == GraphStatus.COMPLETED
    assert log == []

    graph, _ = build_switch(1)
    result = await graph.run()
    assert "must return a str, got int" in result.error


def test_switch_requires_cases():
    with pytest.raises(ValueError, match="requires cases"):
        build_graph({"nodes": [{"name": "s", "type": "switch", "fn": "builtins:str"}]})
