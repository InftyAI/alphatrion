import pytest

from alphatrion.swarm import (
    ActionNode,
    Capability,
    EvaluatorNode,
    GraphStatus,
    Pipeline,
    build_graph,
    check_mutation,
)


def commit(state):
    return state.commit("v1").id


def remember(state):
    state.memory.set("seen", True)


def add_to_tree(state):
    state.tree.add("v1")


def score_directly(state):
    state.tree._set_score(state.current_id, 1.0)


def commits(state) -> bool:
    state.commit("v2")
    return True


def score(state) -> float:
    return 0.5


async def run(nodes):
    graph = build_graph(
        {"nodes": nodes},
        functions={
            fn.__name__: fn
            for fn in (
                commit,
                remember,
                add_to_tree,
                score_directly,
                commits,
                score,
            )
        },
    )
    return await graph.run()


def test_types_declare_their_capabilities():
    assert ActionNode(name="a", fn="f").granted == {
        Capability.COMMIT,
        Capability.REMEMBER,
    }
    assert EvaluatorNode(name="e", fn="f").granted == {Capability.SCORE}
    narrowed = ActionNode(name="a", fn="f", capabilities=["remember"])
    assert narrowed.granted == {Capability.REMEMBER}
    assert ActionNode(name="a", fn="f", capabilities=[]).granted == set()


def test_capabilities_cannot_exceed_the_type():
    with pytest.raises(ValueError, match="action node can't have score"):
        ActionNode(name="a", fn="f", capabilities=["score"])
    with pytest.raises(ValueError, match="condition node can't have commit"):
        Pipeline.model_validate(
            {
                "nodes": [
                    {
                        "name": "c",
                        "type": "condition",
                        "fn": "f",
                        "capabilities": ["commit"],
                    }
                ]
            }
        )


@pytest.mark.asyncio
async def test_actions_commit_and_remember():
    result = await run(
        [
            {"name": "commit", "type": "action", "fn": "commit"},
            {"name": "remember", "type": "action", "fn": "remember"},
        ]
    )
    assert result.status == GraphStatus.COMPLETED, result.error
    assert result.state.current.content == "v1"
    assert result.state.memory.get("seen") is True


@pytest.mark.asyncio
async def test_narrowed_action_cannot_commit():
    result = await run(
        [
            {
                "name": "propose",
                "type": "action",
                "fn": "commit",
                "capabilities": ["remember"],
            }
        ]
    )
    assert result.status == GraphStatus.FAILED
    assert "Node propose has no commit capability, only remember" in result.error
    assert len(result.state.tree) == 0


@pytest.mark.asyncio
async def test_decisions_cannot_change_the_state():
    result = await run(
        [
            {"name": "seed", "type": "action", "fn": "commit"},
            {"name": "check", "type": "condition", "fn": "commits"},
        ]
    )
    assert result.status == GraphStatus.FAILED
    assert "Node check has no commit capability" in result.error


@pytest.mark.asyncio
async def test_evaluators_only_score_what_they_measure():
    result = await run(
        [
            {"name": "seed", "type": "action", "fn": "commit"},
            {"name": "evaluate", "type": "evaluator", "fn": "score"},
        ]
    )
    assert result.status == GraphStatus.COMPLETED, result.error
    assert result.state.current.score == 0.5


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fn, error",
    [
        ("add_to_tree", "AttributeError"),
        ("score_directly", "AttributeError"),
    ],
)
async def test_functions_cannot_bypass_the_view(fn, error):
    result = await run(
        [
            {"name": "seed", "type": "action", "fn": "commit"},
            {"name": "bypass", "type": "action", "fn": fn},
        ]
    )
    assert result.status == GraphStatus.FAILED
    assert result.error.startswith(error)
    assert len(result.state.tree) == 1
    assert result.state.current.score is None


def test_mutation_cannot_gain_capabilities():
    def pipeline(capabilities):
        return Pipeline.model_validate(
            {
                "nodes": [
                    {
                        "name": "propose",
                        "type": "action",
                        "fn": "f",
                        "mutable": True,
                        "capabilities": capabilities,
                    }
                ]
            }
        )

    check_mutation(pipeline(["commit", "remember"]), pipeline(["commit"]))
    with pytest.raises(ValueError, match="propose gained the remember capability"):
        check_mutation(pipeline(["commit"]), pipeline(None))
