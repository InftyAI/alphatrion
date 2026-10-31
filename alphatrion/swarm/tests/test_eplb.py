"""Run the EPLB example's pipeline, with ADRS's evaluator, on a tiny
expert-load trace with a scripted model, so it is tested without API keys
or the real trace. Skipped without torch, which ADRS's code needs."""

import json
import random
import sys
from pathlib import Path

import pytest

from alphatrion.swarm import ModelResponse, ScoreMode, State, build_graph
from alphatrion.swarm.nodes import Candidate
from alphatrion.swarm.pipeline import load_pipeline

pytest.importorskip("torch")

EXAMPLE = Path(__file__).parents[3] / "examples" / "cases" / "eplb"
sys.path.insert(0, str(EXAMPLE))

import eplb  # noqa: E402


def edit(search: str, replace: str, description: str) -> str:
    return (
        f"<<<<<<< SEARCH\n{search}\n=======\n{replace}\n>>>>>>> REPLACE\n"
        f"Description: {description}"
    )


class ScriptedModel:
    """Answers each request with the next reply of the script."""

    def __init__(self, replies: list[str]):
        self.replies = iter(replies)
        self.requests = []

    async def complete(self, model, request, max_tokens, params):
        self.requests.append(request)
        return ModelResponse(text=next(self.replies), model="scripted")


@pytest.fixture
def data(tmp_path):
    """A trace in the real one's format: 2 layers of 256 experts, a few hot
    ones, over 300 steps, so 3 windows."""
    rng = random.Random(0)
    hot = [rng.sample(range(256), 8) for _ in range(2)]
    history = [
        {
            "step": step,
            "logical_expert_load": [
                [
                    rng.randint(500, 1000) if e in hot[layer] else rng.randint(0, 5)
                    for e in range(256)
                ]
                for layer in range(2)
            ],
        }
        for step in range(300)
    ]
    (tmp_path / "expert-load.json").write_text(json.dumps({"load_history": history}))
    return tmp_path


@pytest.mark.asyncio
async def test_eplb(data):
    model = ScriptedModel(
        [
            edit("if num_groups % num_nodes == 0:", "if False:", "global policy"),
            edit('__all__ = ["rebalance_experts"]', "__all__ = []", "outside"),
            edit(
                "    num_layers, num_logical_experts = weight.shape\n"
                "    weight = weight.float().cpu()",
                '    raise ValueError("boom")',
                "raises",
            ),
            "I would try a greedy packing.",
        ]
    )
    pipeline = load_pipeline(EXAMPLE / "pipeline.yaml")
    evolve = next(n for n in pipeline.nodes if n.name == "evolve")
    evolve.max_iters = 4
    propose = next(n for n in evolve.nodes if n.name == "propose")
    propose.candidates = [Candidate(model="scripted", provider="model")]

    graph = build_graph(pipeline, functions={**eplb.FUNCTIONS, "model": model})
    state = State()
    result = await graph.run(
        state=state,
        inputs={"data": str(data), "instructions": str(EXAMPLE / "proposer.md")},
    )
    assert result.status.value == "completed", result.error

    # Every program in the tree, as the model saw it: the guard rejected the
    # one editing outside the evolve block, and the one raising scored 0, as
    # in ADRS. The reply without edits added none.
    lines = eplb.history(state).splitlines()
    assert len(lines) == 4
    assert lines[0].endswith(": initial program") and not lines[0].startswith(
        "- 0.0000"
    )
    assert lines[1].endswith(": global policy") and not lines[1].startswith("- 0.0000")
    assert lines[2] == "- rejected: outside"
    assert lines[3] == "- 0.0000: raises"

    # Only the evaluators scored, and the best is a program that improved on
    # nothing worse than the seed.
    seed, policy = (
        a
        for a in state.tree
        if a.metadata["description"] in ("initial program", "global policy")
    )
    assert seed.score > 0 and policy.score > 0
    assert state.tree.best(ScoreMode.MAX) in (seed, policy)
    # Each edited program links to the request, and model, it came from.
    assert policy.metadata["request"] == 1
    assert state.requests.get(1).model == policy.metadata["model"] == "scripted"
    assert len(state.requests) == 4
    # The model saw how every program did.
    assert "- rejected: outside" in model.requests[-1].messages[0]["content"]


def test_an_optimizer_may_change_the_method_but_not_the_judge():
    from alphatrion.swarm import check_mutation

    original = load_pipeline(EXAMPLE / "pipeline.yaml")

    def changed(change):
        pipeline = load_pipeline(EXAMPLE / "pipeline.yaml")
        change({n.name: n for n in [*pipeline.nodes, *pipeline.nodes[2].nodes]})
        return pipeline

    # The method: more iterations, other models, other instructions.
    def method(nodes):
        nodes["evolve"].max_iters = 50
        nodes["propose"].candidates = nodes["propose"].candidates[:1]
        nodes["prompt"].params["instructions"] = "${inputs.instructions}"

    check_mutation(original, changed(method))

    # The judge: the guard's checks and the evaluator.
    def guard(nodes):
        nodes["guard"].checks = []

    def evaluator(nodes):
        nodes["evaluate"].fn = "always_one"

    for change, error in [
        (guard, "guard was changed"),
        (evaluator, "evaluate was changed"),
    ]:
        with pytest.raises(ValueError, match=error):
            check_mutation(original, changed(change))


@pytest.mark.asyncio
async def test_a_continued_experiment_keeps_one_seed(data, tmp_path):
    from alphatrion.swarm import HostStore

    store = HostStore(tmp_path / "experiments", experiment="eplb")
    inputs = {"data": str(data), "instructions": str(EXAMPLE / "proposer.md")}
    for _ in range(2):
        pipeline = load_pipeline(EXAMPLE / "pipeline.yaml")
        next(n for n in pipeline.nodes if n.name == "evolve").max_iters = 1
        model = ScriptedModel(
            [edit("if num_groups % num_nodes == 0:", "if False:", "global")]
        )
        propose = next(n for n in pipeline.nodes[2].nodes if n.name == "propose")
        propose.candidates = [Candidate(model="scripted", provider="model")]
        graph = build_graph(pipeline, functions={**eplb.FUNCTIONS, "model": model})
        result = await graph.run(state=store.load(), inputs=inputs, store=store)
        assert result.status.value == "completed", result.error
    roots = [
        a
        for a in store.load().tree
        if a.metadata.get("description") == "initial program"
    ]
    assert len(roots) == 1
