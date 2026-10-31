import asyncio

import pytest

from alphatrion.swarm import (
    BREAK,
    END,
    ActionNode,
    Choice,
    ConditionNode,
    EvaluatorNode,
    Graph,
    GraphStatus,
    GuardrailNode,
    LoopNode,
    ParallelNode,
    State,
)


def branch_index(state: State) -> int:
    # Branches are named like "explore[2]".
    return int(state.branch.rsplit("[", 1)[1].rstrip("]"))


def build_debug_loop(passes_after: int, max_iters: int = 3) -> LoopNode:
    """Run, check, and fix until the check passes."""

    def run(state: State):
        attempts = state.memory.get("attempts", 0) + 1
        state.memory.set("attempts", attempts)
        return state.commit(attempts)

    def passes(state: State):
        return state.current.content >= passes_after

    return LoopNode(
        name="debug",
        max_iters=max_iters,
        nodes=[
            ActionNode(name="run", fn=run),
            GuardrailNode(
                name="check",
                checks=[passes],
                exit={"pass": BREAK},
                branches={"fail": [ActionNode(name="fix", fn=lambda state: None)]},
            ),
        ],
    )


def seeded() -> State:
    state = State()
    state.commit("seed")
    return state


def wrap(node, after=END) -> Graph:
    return Graph().add_node(node).add_edge(node.name, after)


def outer(loop: LoopNode) -> Graph:
    return (
        Graph()
        .add_node(loop)
        .add_node(ActionNode(name="ship", fn=lambda state: "shipped"))
        .add_node(ActionNode(name="give_up", fn=lambda state: "gave up"))
        .add_edge(loop.name, "ship", when="completed")
        .add_edge(loop.name, "give_up", when="max_iters")
    )


@pytest.mark.asyncio
async def test_loop_breaks():
    result = await outer(build_debug_loop(passes_after=2)).run()
    assert result.path == ["debug", "ship"]
    assert result.state.memory.history(node="debug")[0].data["details"] == {
        "iterations": 2
    }
    # The body records into the same memory.
    assert len(result.state.memory.history(node="run")) == 2
    assert len(result.state.memory.history(node="fix")) == 1


@pytest.mark.asyncio
async def test_loop_exhausted():
    result = await outer(build_debug_loop(passes_after=10, max_iters=3)).run()
    assert result.path == ["debug", "give_up"]
    assert len(result.state.memory.history(node="run")) == 3


@pytest.mark.asyncio
async def test_loop_until():
    def improve(state: State):
        state.commit((state.current.content if state.current else 0) + 1)

    loop = LoopNode(
        name="improve_loop",
        nodes=[ActionNode(name="improve", fn=improve)],
        max_iters=10,
        until=lambda state, target: state.current.content >= target,
        params={"target": 4},
    )
    result = await wrap(loop).run()
    assert result.status == GraphStatus.COMPLETED
    assert result.state.current.content == 4


@pytest.mark.asyncio
async def test_loop_failure_fails_parent():
    def broken(state: State):
        raise ValueError("boom")

    loop = LoopNode(
        name="loop",
        nodes=[ActionNode(name="broken", fn=broken)],
        max_iters=3,
    )
    result = await wrap(loop).run()
    assert result.status == GraphStatus.FAILED
    assert "iteration 1" in result.error


def test_loop_invalid():
    body = [ActionNode(name="a", fn=lambda state: None)]
    with pytest.raises(ValueError):
        LoopNode(name="loop", nodes=body, max_iters=0)
    with pytest.raises(ValueError):
        LoopNode(name="loop", nodes=[])
    # continue and break are only targets of graphs that declare them.
    with pytest.raises(KeyError):
        Graph().add_node(ActionNode(name="a", fn=lambda state: None)).add_edge(
            "a", BREAK
        )


def build_explore(**kwargs) -> ParallelNode:
    def propose(state: State):
        return state.commit(f"variant-{branch_index(state)}")

    def score(state: State):
        # Branch 1 proposes the best variant.
        return {0: 0.2, 1: 0.9, 2: 0.5}[branch_index(state)]

    return ParallelNode(
        name="explore",
        n=3,
        nodes=[
            ActionNode(name="propose", fn=propose),
            EvaluatorNode(name="evaluate", fn=score),
        ],
        **kwargs,
    )


@pytest.mark.asyncio
async def test_parallel_join_best():
    state = State()
    root = state.commit("seed")
    result = await wrap(build_explore()).run(state=state)

    assert result.status == GraphStatus.COMPLETED
    assert state.current.content == "variant-1"
    # Every branch derived its variant from the parent's current artifact.
    assert sorted(a.content for a in state.tree.children(root.id)) == [
        "variant-0",
        "variant-1",
        "variant-2",
    ]
    branches = {e.data["branch"] for e in state.memory.history(node="propose")}
    assert branches == {"explore[0]", "explore[1]", "explore[2]"}


@pytest.mark.asyncio
async def test_parallel_join_all_and_custom():
    state = State()
    state.commit("seed")
    result = await wrap(build_explore(join="all")).run(state=state)
    # join="all" outputs every branch's value, here its Metrics.
    outputs = result.output
    assert [m.score for m in outputs] == [0.2, 0.9, 0.5]
    # join="all" doesn't move the parent's current artifact.
    assert state.current.content == "seed"

    def pick(state: State, results, target: float):
        best = max(r.state.current.score for r in results)
        raise Choice("good" if best >= target else "bad")

    graph = (
        Graph()
        .add_node(build_explore(join=pick, params={"target": 0.8}))
        .add_edge("explore", END, when="good")
    )
    result = await graph.run(state=seeded())
    assert result.status == GraphStatus.COMPLETED


def build_racers(wait: int | None, fail: set[int], raises: set[int] = frozenset()):
    finished = []

    async def race(state: State):
        i = branch_index(state)
        # Branch i finishes after i ticks, so lower branches finish first.
        for _ in range(i * 5):
            await asyncio.sleep(0)
        if i in fail:
            raise ValueError(f"branch {i} broke")
        finished.append(i)
        return state.commit(i)

    def ok(state: State):
        return branch_index(state) not in raises

    node = ParallelNode(
        name="race",
        n=4,
        wait=wait,
        join="all",
        nodes=[
            ActionNode(name="race_step", fn=race),
            GuardrailNode(name="guard", checks=[ok], exit={"fail": "raise"}),
            EvaluatorNode(name="evaluate", fn=lambda state: state.current.content),
        ],
    )
    return node, finished


@pytest.mark.asyncio
async def test_parallel_wait_for_k_cancels_the_rest():
    node, finished = build_racers(wait=2, fail={0})
    result = await wrap(node).run(state=seeded())

    assert result.status == GraphStatus.COMPLETED
    assert [m.score for m in result.output] == [1, 2]
    # Branch 3 was cancelled before it finished.
    assert finished == [1, 2]


@pytest.mark.asyncio
async def test_parallel_wait_all_fails_on_any_failure():
    node, finished = build_racers(wait=None, fail={2})
    result = await wrap(node).run(state=seeded())
    assert result.status == GraphStatus.FAILED
    assert "branch 2 broke" in result.error
    # The failed branch didn't stop the others, which all ran to their end.
    assert sorted(finished) == [0, 1, 3]


@pytest.mark.asyncio
async def test_parallel_not_enough_finished():
    node, _ = build_racers(wait=3, fail={0, 1})
    result = await wrap(node).run(state=seeded())
    assert result.status == GraphStatus.FAILED
    assert "needs 3 finished branches, got 2" in result.error


@pytest.mark.asyncio
async def test_parallel_raise_only_fails_its_branch():
    # Branch 0 raises, which fails only its own run, so with wait=2 it's
    # ignored like any failed branch.
    node, _ = build_racers(wait=2, fail=set(), raises={0})
    result = await wrap(node).run(state=seeded())
    assert result.status == GraphStatus.COMPLETED
    assert [m.score for m in result.output] == [1, 2]


@pytest.mark.asyncio
async def test_parallel_loops_until_cancelled():
    async def tick(state: State):
        await asyncio.sleep(0)

    workers = ParallelNode(
        name="workers",
        n=3,
        join="all",
        nodes=[LoopNode(name="ticker", nodes=[ActionNode(name="tick", fn=tick)])],
    )
    state = State()
    task = asyncio.create_task(wrap(workers).run(state=state))
    while len(state.memory) < 30:
        await asyncio.sleep(0)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # All the branches stopped with the parent.
    stopped = len(state.memory)
    for _ in range(10):
        await asyncio.sleep(0)
    assert len(state.memory) == stopped
    branches = {e.data["branch"] for e in state.memory}
    assert branches == {"workers[0]", "workers[1]", "workers[2]"}


def test_parallel_invalid():
    def body():
        return [ActionNode(name="a", fn=lambda state: None)]

    with pytest.raises(ValueError):
        ParallelNode(name="p", nodes=body(), n=0)
    with pytest.raises(ValueError):
        ParallelNode(name="p", nodes=body(), n=2, wait=3)
    # An unknown join is neither a built-in nor a resolvable function.
    with pytest.raises(KeyError):
        Graph().add_node(ParallelNode(name="p", nodes=body(), n=2, join="unknown"))


@pytest.mark.asyncio
async def test_parallel_sync_branches_interleave():
    # Sync nodes never await, but branches still take turns, so a fast
    # branch doesn't run to completion before the others start.
    started = set()

    def step(state: State):
        started.add(branch_index(state))
        state.memory.set(state.branch, state.memory.get(state.branch, 0) + 1)

    loop = LoopNode(
        name="work",
        nodes=[ActionNode(name="step", fn=step)],
        until=lambda state: state.memory.get(state.branch) >= 5 + branch_index(state),
    )
    parallel = ParallelNode(name="p", nodes=[loop], n=3, wait=1, join="all")
    result = await wrap(parallel).run()

    assert result.status == GraphStatus.COMPLETED
    assert started == {0, 1, 2}


@pytest.mark.asyncio
async def test_end_stops_the_whole_run():
    log = []

    def step(state: State):
        log.append(state.node)

    loop = LoopNode(
        name="loop",
        max_iters=5,
        nodes=[
            ActionNode(name="step", fn=step),
            ActionNode(name="stop", fn=step, exit="end"),
        ],
    )
    graph = (
        Graph()
        .add_node(loop)
        .add_node(ActionNode(name="after", fn=step))
        .add_edge("loop", "after")
    )
    result = await graph.run()
    # end inside the loop stops the run: no more iterations, nor the node after.
    assert result.status == GraphStatus.COMPLETED
    assert result.exit == END
    assert log == ["step", "stop"]


@pytest.mark.asyncio
async def test_end_in_a_parallel_branch_only_ends_the_branch():
    async def work(state: State):
        for _ in range(10 * branch_index(state)):
            await asyncio.sleep(0)

    parallel = ParallelNode(
        name="p",
        n=3,
        join="all",
        nodes=[
            ActionNode(name="work", fn=work),
            ActionNode(name="stop", fn=lambda state: None, exit="end"),
        ],
    )
    graph = (
        Graph()
        .add_node(parallel)
        .add_node(ActionNode(name="after", fn=lambda state: None))
        .add_edge("p", "after")
    )
    result = await graph.run()
    # Each branch is its own run: ending one doesn't stop the others, nor
    # the graph around the parallel node.
    assert result.status == GraphStatus.COMPLETED
    assert result.path == ["p", "after"]
    assert len(result.state.memory.history(node="stop")) == 3


@pytest.mark.asyncio
async def test_raise_fails_the_run_from_any_node():
    loop = LoopNode(
        name="loop",
        max_iters=5,
        nodes=[
            ConditionNode(name="bad", fn=lambda state: True, exit={"true": "raise"}),
        ],
    )
    result = await wrap(loop).run()
    assert result.status == GraphStatus.FAILED
    assert "bad raised on choice 'true'" in result.error
