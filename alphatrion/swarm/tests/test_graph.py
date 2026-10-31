import asyncio

import pytest

from alphatrion.swarm import (
    BREAK,
    CONTINUE,
    END,
    RAISE,
    ActionNode,
    Choice,
    ChoiceError,
    ConditionNode,
    EvaluatorNode,
    Graph,
    GraphStatus,
    GuardrailNode,
    LoopNode,
    State,
)


def propose(state: State, step: int = 1):
    # Improve on the best artifact so far, which is how a branch that
    # doesn't improve gets abandoned.
    best = state.tree.best()
    if best is not None:
        state.checkout(best.id)
    base = state.current.content if state.current else 0
    return state.commit(base + step)


def not_negative(state: State):
    return state.current.content >= 0, "artifact is negative"


def score(state: State):
    # The artifact the node before committed.
    return state.current.content


def good_enough(state: State, target: int):
    return state.current.score >= target


def build_rsi_graph(target: int = 3, max_iters: int | None = None) -> Graph:
    loop = LoopNode(
        name="improve",
        max_iters=max_iters,
        until=good_enough,
        params={"target": target},
        nodes=[
            ActionNode(name="propose", fn=propose),
            GuardrailNode(name="guard", checks=[not_negative], exit={"fail": CONTINUE}),
            EvaluatorNode(name="evaluate", fn=score),
        ],
    )
    return Graph(name="rsi").add_node(loop)


@pytest.mark.asyncio
async def test_improvement_loop():
    result = await build_rsi_graph(target=3).run()

    assert result.status == GraphStatus.COMPLETED
    assert result.path == ["improve"]
    state = result.state
    assert [a.content for a in state.tree.lineage(state.current_id)] == [1, 2, 3]
    assert state.tree.best().score == 3
    assert all(a.created_by == "propose" for a in state.tree)
    assert state.memory.history(node="improve")[0].data["details"] == {"iterations": 3}
    assert len(state.memory.history(node="propose")) == 3


@pytest.mark.asyncio
async def test_resume_from_state():
    first = await build_rsi_graph(target=2).run()
    second = await build_rsi_graph(target=4).run(state=first.state)

    assert second.status == GraphStatus.COMPLETED
    state = second.state
    assert [a.content for a in state.tree.lineage(state.current_id)] == [1, 2, 3, 4]
    assert len(state.memory.history(node="improve")) == 2


@pytest.mark.asyncio
async def test_loop_max_iters():
    result = await build_rsi_graph(target=100, max_iters=5).run()
    assert result.status == GraphStatus.COMPLETED
    loop = result.state.memory.history(node="improve")[0]
    assert loop.data["choice"] == "max_iters"
    assert loop.data["details"] == {"iterations": 5}


@pytest.mark.asyncio
async def test_guardrail_choices_on_fail():
    calls = []

    def propose_negative(state: State):
        calls.append(1)
        return state.commit(-1 if len(calls) == 1 else 1)

    loop = LoopNode(
        name="retry",
        max_iters=5,
        nodes=[
            ActionNode(name="propose", fn=propose_negative),
            GuardrailNode(
                name="guard",
                checks=[not_negative],
                exit={"fail": CONTINUE, "pass": BREAK},
            ),
        ],
    )
    result = await Graph().add_node(loop).run()

    assert result.status == GraphStatus.COMPLETED
    guard = result.state.memory.history(node="guard")
    assert [e.data["choice"] for e in guard] == ["fail", "pass"]
    assert guard[0].data["details"] == ["artifact is negative"]
    assert guard[1].data["details"] == []


def test_cycles_rejected():
    graph = (
        Graph()
        .add_node(ActionNode(name="a", fn=lambda state: None))
        .add_node(ActionNode(name="b", fn=lambda state: None))
        .add_edge("a", "b")
        .add_edge("b", "a")
    )
    with pytest.raises(ValueError, match="cycle a -> b -> a"):
        graph.validate()


@pytest.mark.asyncio
async def test_guardrail_raise_fails_the_run():
    graph = (
        Graph()
        .add_node(ActionNode(name="propose", fn=lambda state: state.commit(-1)))
        .add_node(GuardrailNode(name="guard", checks=[not_negative]))
        .add_edge("propose", "guard")
        .add_edge("guard", END, when="pass")
        .add_edge("guard", RAISE, when="fail")
    )
    result = await graph.run()

    assert result.status == GraphStatus.FAILED
    assert "guard raised on choice 'fail'" in result.error
    assert "artifact is negative" in result.error


def test_guardrail_requires_fail_edge():
    graph = (
        Graph()
        .add_node(GuardrailNode(name="guard", checks=[not_negative]))
        .add_edge("guard", END, when="pass")
    )
    with pytest.raises(ValueError, match="fail"):
        graph.validate()


@pytest.mark.asyncio
async def test_async_nodes_and_custom_choice():
    # kind is an input of the run, which classify gets as a param.
    async def classify(state: State, kind: str):
        raise Choice(kind)

    graph = (
        Graph(inputs={"kind"})
        .add_node(
            ActionNode(name="classify", fn=classify, params={"kind": "${inputs.kind}"})
        )
        .add_node(ActionNode(name="small", fn=lambda state: "small"))
        .add_node(ActionNode(name="large", fn=lambda state: "large"))
        .add_edge("classify", "small", when="small")
        .add_edge("classify", "large")
    )

    result = await graph.run(inputs={"kind": "small"})
    assert result.path == ["classify", "small"]
    # An unmatched choice falls back to the default edge.
    result = await graph.run(inputs={"kind": "medium"})
    assert result.path == ["classify", "large"]


@pytest.mark.asyncio
async def test_unmatched_choice_fails():
    graph = (
        Graph()
        .add_node(ConditionNode(name="check", fn=lambda state: False))
        .add_edge("check", END, when="true")
    )
    result = await graph.run()
    assert result.status == GraphStatus.FAILED
    assert ChoiceError.__name__ in result.error


@pytest.mark.asyncio
async def test_condition_must_return_bool():
    graph = Graph().add_node(ConditionNode(name="check", fn=lambda state: "maybe"))
    result = await graph.run()
    assert result.status == GraphStatus.FAILED
    assert "must return a bool, got str" in result.error


@pytest.mark.asyncio
async def test_node_exception_fails():
    def broken(state: State):
        raise ValueError("boom")

    result = await Graph().add_node(ActionNode(name="broken", fn=broken)).run()
    assert result.status == GraphStatus.FAILED
    assert result.error == "ValueError: boom"


def test_node_fields_are_validated():
    with pytest.raises(ValueError):
        ActionNode(name="a")
    with pytest.raises(ValueError):
        ActionNode(name="a", fn=print, max_iters=3)
    with pytest.raises(ValueError):
        GuardrailNode(name="g", checks=[])


def test_invalid_graph():
    graph = Graph().add_node(ActionNode(name="a", fn=lambda state: None))
    with pytest.raises(ValueError):
        graph.add_node(ActionNode(name="a", fn=lambda state: None))
    with pytest.raises(ValueError):
        graph.add_node(ActionNode(name=END, fn=lambda state: None))
    with pytest.raises(KeyError):
        graph.add_edge("a", "missing")
    graph.add_edge("a", END)
    with pytest.raises(ValueError):
        graph.add_edge("a", END)


@pytest.mark.asyncio
async def test_unbounded_loop_stops_on_task_cancel():
    # With max_iters=None a loop runs until its task is cancelled, which is
    # how the framework stops a run.
    async def tick(state: State):
        await asyncio.sleep(0)

    loop = LoopNode(name="forever", nodes=[ActionNode(name="tick", fn=tick)])
    graph = Graph().add_node(loop)
    state = State()

    task = asyncio.create_task(graph.run(state=state))
    while len(state.memory) < 10:
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert state.node is None
