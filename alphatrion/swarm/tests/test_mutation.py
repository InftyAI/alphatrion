import pytest
import yaml

from alphatrion.swarm import ActionNode, Pipeline, check_mutation

PIPELINE = """
name: rsi
nodes:
  - name: improve
    type: loop
    max_iters: 10
    mutable: true
    nodes:
      - {name: propose, type: action, fn: propose, mutable: true}
      - name: guard
        type: guardrail
        checks: [is_valid]
        exit: {fail: continue}
      - name: attempt
        nodes:
          - {name: run, type: action, fn: run}
          - {name: evaluate, type: evaluator, fn: score}
"""


def pipeline(text: str = PIPELINE) -> Pipeline:
    return Pipeline.model_validate(yaml.safe_load(text))


def test_nodes_are_immutable_by_default():
    nodes = pipeline().nodes
    assert nodes[0].mutable
    assert not ActionNode(name="a", fn="f").mutable


@pytest.mark.parametrize("type_", ["evaluator", "guardrail"])
def test_judges_are_always_immutable(type_):
    field = "fn: score" if type_ == "evaluator" else "checks: [is_valid]"
    with pytest.raises(ValueError, match="always immutable"):
        pipeline(f"nodes: [{{name: judge, type: {type_}, {field}, mutable: true}}]")


def test_mutable_nodes_can_change():
    mutated = pipeline(
        PIPELINE.replace("max_iters: 10", "max_iters: 50").replace(
            "fn: propose", "fn: propose_v2"
        )
    )
    check_mutation(pipeline(), mutated)


def test_nodes_can_be_added_but_not_evaluators():
    guard = (
        "      - {name: novel, type: guardrail, checks: [is_novel], exit: continue}\n"
    )
    added = PIPELINE.replace("      - name: guard\n", guard + "      - name: guard\n")
    check_mutation(pipeline(), pipeline(added))

    evaluator = "      - {name: judge, type: evaluator, fn: always_1}\n"
    added = PIPELINE.replace(
        "      - name: guard\n", evaluator + "      - name: guard\n"
    )
    with pytest.raises(ValueError, match="judge was added with the score capability"):
        check_mutation(pipeline(), pipeline(added))


@pytest.mark.parametrize(
    "old, new, error",
    [
        # An immutable node, in a mutable loop.
        ("checks: [is_valid]", "checks: [always_true]", "guard was changed"),
        ("        exit: {fail: continue}\n", "", "guard was changed"),
        # A node nested in an immutable subgraph changes the subgraph too.
        ("fn: run}", "fn: run_v2}", "attempt was changed"),
        ("fn: score}", "fn: always_1}", "attempt"),
    ],
)
def test_immutable_nodes_cannot_change(old, new, error):
    with pytest.raises(ValueError, match=error):
        check_mutation(pipeline(), pipeline(PIPELINE.replace(old, new)))


def test_immutable_nodes_cannot_be_removed():
    removed = PIPELINE.split("      - name: attempt")[0]
    with pytest.raises(ValueError, match="attempt was removed"):
        check_mutation(pipeline(), pipeline(removed))


def test_subgraph_nodes_are_scoped():
    # A mutable subgraph keeps its immutable nodes, named attempt.<name>.
    mutable = PIPELINE.replace(
        "      - name: attempt\n", "      - name: attempt\n        mutable: true\n"
    )
    with pytest.raises(ValueError, match="attempt.run was changed"):
        check_mutation(
            pipeline(mutable), pipeline(mutable.replace("fn: run}", "fn: run_v2}"))
        )
    mutable = mutable.replace("fn: run}", "fn: run, mutable: true}")
    changed = mutable.replace("fn: run,", "fn: run_v2,")
    check_mutation(pipeline(mutable), pipeline(changed))
    with pytest.raises(ValueError, match="attempt.evaluate was changed"):
        check_mutation(
            pipeline(mutable), pipeline(mutable.replace("fn: score}", "fn: always_1}"))
        )
