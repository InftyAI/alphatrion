from typing import Any, Literal

import pytest

from alphatrion.swarm import (
    DecisionNode,
    Execution,
    Files,
    GraphStatus,
    Metrics,
    State,
    Text,
    build_graph,
)
from alphatrion.swarm.formats import compatible


class TrainingRun(Execution):
    """An extended format, accepted wherever an Execution is."""

    peak_vram_gb: float


def read(state) -> Files:
    return Files(files={"train.py": "lr = 1"})


def run(state, code: Files) -> Execution:
    return Execution(exit_code=0, stdout="val_bpb: 0.9", duration=1.0)


def train(state, code: Files) -> TrainingRun:
    return TrainingRun(exit_code=0, duration=1.0, peak_vram_gb=12.5)


def measure(state, result: Execution) -> Metrics:
    return Metrics(values={"val_bpb": 0.9}, primary="val_bpb", lower_is_better=True)


FUNCTIONS = {fn.__name__: fn for fn in (read, run, train, measure)}


def node(name, fn=None, **params):
    return {"name": name, "type": "action", "fn": fn or name, "params": params}


def build(*nodes, **kwargs):
    return build_graph({"nodes": list(nodes), **kwargs}, functions=FUNCTIONS)


@pytest.mark.asyncio
async def test_outputs_flow_by_reference():
    result = await build(
        node("read"),
        node("run", code="${nodes.read.output}"),
        node("measure", result="${nodes.run.output}"),
    ).run()
    assert result.status == GraphStatus.COMPLETED, result.error
    # The run's output is its last one.
    assert result.output.score == 0.9
    # Every node's output is recorded in memory.
    assert isinstance(
        result.state.memory.history(node="run")[0].data["output"], Execution
    )


@pytest.mark.asyncio
async def test_a_reference_can_skip_nodes():
    result = await build(
        node("read"),
        node("run", code="${nodes.read.output}"),
        # read's output, two nodes back.
        node("again", fn="run", code="${nodes.read.output}"),
    ).run()
    assert result.status == GraphStatus.COMPLETED, result.error


def test_mismatched_reference_fails_at_load():
    with pytest.raises(
        ValueError,
        match=r"Node measure param result takes Execution, but "
        r"\$\{nodes.read.output\} is Files",
    ):
        build(node("read"), node("measure", result="${nodes.read.output}"))


@pytest.mark.asyncio
async def test_extended_formats_fit_their_base():
    result = await build(
        node("read"),
        node("train", code="${nodes.read.output}"),
        node("measure", result="${nodes.train.output}"),
    ).run()
    assert result.status == GraphStatus.COMPLETED, result.error
    assert compatible(TrainingRun, Execution)
    assert not compatible(Execution, TrainingRun)


def check_true(state) -> bool:
    return True


def test_only_nodes_that_always_ran_with_an_output_can_be_referenced():
    branch = {
        "name": "maybe",
        "type": "condition",
        "fn": check_true,
        "branches": {"true": [node("run", code="${nodes.read.output}")]},
    }
    cases = [
        # A later node.
        (
            [
                node("measure", result="${nodes.run.output}"),
                node("read"),
                node("run", code="${nodes.read.output}"),
            ],
            "run is not a node that always runs before it",
        ),
        # An unknown node.
        ([node("run", code="${nodes.nope.output}")], "nope is not a node"),
        # A node in a branch, which may not run.
        (
            [node("read"), branch, node("measure", result="${nodes.run.output}")],
            "run is not a node",
        ),
        # A decision, which has no output.
        (
            [
                {"name": "check", "type": "condition", "fn": check_true},
                node("run", code="${nodes.check.output}"),
            ],
            "check is not a node",
        ),
    ]
    for nodes, error in cases:
        with pytest.raises(ValueError, match=error):
            build(*nodes)


@pytest.mark.asyncio
async def test_a_branch_sees_what_ran_before_its_node():
    result = await build(
        node("read"),
        {
            "name": "check",
            "type": "condition",
            "fn": check_true,
            "branches": {"true": [node("run", code="${nodes.read.output}")]},
        },
    ).run()
    assert result.status == GraphStatus.COMPLETED, result.error
    assert result.path == ["read", "check", "run"]


@pytest.mark.asyncio
async def test_wrong_output_fails_at_run_time():
    def liar(state) -> Files:
        return Text(content="not files")

    result = await build_graph(
        {"nodes": [{"name": "liar", "type": "action", "fn": liar}]}
    ).run()
    assert result.status == GraphStatus.FAILED
    assert "liar returned the wrong format, expected Files" in result.error


def zero(state) -> int:
    return 0


def count(state, start: int) -> int:
    state.memory.set("n", state.memory.get("n", start) + 1)
    return state.memory.get("n")


def odd(state, n: int) -> bool:
    return n % 2 == 1


def same(state, n: int) -> int:
    return n


@pytest.mark.asyncio
async def test_a_loop_outputs_its_last_iteration_not_discarded():
    graph = build_graph(
        {
            "nodes": [
                {"name": "zero", "type": "action", "fn": zero},
                {
                    "name": "repeat",
                    "type": "loop",
                    "max_iters": 5,
                    "nodes": [
                        {
                            "name": "count",
                            "type": "action",
                            "fn": count,
                            "params": {"start": "${nodes.zero.output}"},
                        },
                        # Odd iterations are discarded.
                        {
                            "name": "odd",
                            "type": "condition",
                            "fn": odd,
                            "params": {"n": "${nodes.count.output}"},
                            "exit": {"true": "continue"},
                        },
                    ],
                },
                {
                    "name": "after",
                    "type": "action",
                    "fn": same,
                    "params": {"n": "${nodes.repeat.output}"},
                },
            ]
        }
    )
    result = await graph.run()
    assert result.status == GraphStatus.COMPLETED, result.error
    # 1 to 5: 5 is the last, but odd, so discarded.
    assert result.output == 4


@pytest.mark.asyncio
async def test_untyped_functions_take_any_format():
    def anything(state, x):
        return x

    result = await build(
        node("read"),
        {
            "name": "anything",
            "type": "action",
            "fn": anything,
            "params": {"x": "${nodes.read.output}"},
        },
    ).run()
    assert result.status == GraphStatus.COMPLETED, result.error


def test_format_helpers():
    assert compatible(int, float)
    assert compatible(Files, Files | Text)
    assert compatible(Any, Files)
    assert not compatible(Files | Text, Files)
    with pytest.raises(ValueError):
        Metrics(values={"a": 1.0}, primary="b")


class BudgetNode(DecisionNode):
    """A custom decision: only decide() is needed."""

    type: Literal["budget"] = "budget"
    limit: int

    async def decide(self, state):
        spent = state.memory.get("spent", 0)
        return ("over" if spent > self.limit else "within"), spent


@pytest.mark.asyncio
async def test_custom_decision_node():
    pipeline = {
        "nodes": [
            node("read"),
            {"name": "budget", "type": "budget", "limit": 10, "exit": {"over": "end"}},
            # A decision has no output, so run references read's.
            node("run", code="${nodes.read.output}"),
        ]
    }
    graph = build_graph(pipeline, node_types=[BudgetNode], functions=FUNCTIONS)
    result = await graph.run()
    assert result.path == ["read", "budget", "run"]
    assert result.state.memory.history(node="budget")[0].data["details"] == 0

    state = State()
    state.memory.set("spent", 20)
    result = await graph.run(state=state)
    assert result.path == ["read", "budget"]


@pytest.mark.asyncio
async def test_a_loop_without_an_iteration_has_no_output():
    graph = build_graph(
        {
            "nodes": [
                {
                    "name": "never",
                    "type": "loop",
                    "max_iters": 1,
                    "nodes": [
                        {
                            "name": "zero",
                            "type": "action",
                            "fn": zero,
                            "exit": "continue",
                        }
                    ],
                },
                {
                    "name": "after",
                    "type": "action",
                    "fn": same,
                    "params": {"n": "${nodes.never.output}"},
                },
            ]
        }
    )
    result = await graph.run()
    assert result.status == GraphStatus.FAILED
    assert "never has no output" in result.error
