import pytest
import pytest_asyncio

from alphatrion.swarm import Files, HostStore, build_graph
from alphatrion.swarm.show import Style, artifact, chart, overview

PLAIN = Style(False)


def propose(state) -> Files:
    n = len(state.tree)
    files = Files(files={"p.py": f"n = {n}\n"})
    state.commit(files, metadata={"description": f"n is {n}"})
    return files


def score(state, program: Files) -> float:
    return float(program.files["p.py"].split("=")[1])


@pytest_asyncio.fixture
async def experiment(tmp_path):
    graph = build_graph(
        {
            "nodes": [
                {
                    "name": "improve",
                    "type": "loop",
                    "max_iters": 3,
                    "nodes": [
                        {"name": "propose", "type": "action", "fn": propose},
                        {
                            "name": "evaluate",
                            "type": "evaluator",
                            "fn": score,
                            "params": {"program": "${nodes.propose.output}"},
                        },
                    ],
                }
            ]
        }
    )
    store = HostStore(tmp_path, experiment="count")
    result = await graph.run(store=store)
    return store.path, result.state


@pytest.mark.asyncio
async def test_the_overview(experiment):
    path, state = experiment
    text = overview(path, PLAIN)
    best = state.tree.best()
    assert f"best score  2.0000  {best.id[:8]}  n is 2" in text
    assert "programs    3 (3 scored), 3 evaluations" in text
    assert "runs        1, the last completed" in text
    # The tree, as tree.render() draws it.
    assert state.tree.render() in text


@pytest.mark.asyncio
async def test_an_artifact(experiment):
    path, state = experiment
    best = state.tree.best()
    text = artifact(path, best.id[:6], PLAIN)
    assert text.startswith(f"Program {best.id[:8]}  2.0000")
    assert "iteration            improve 3" in text
    assert "+n = 2" in text and "-n = 1" in text
    with pytest.raises(SystemExit, match="No artifacts start with 'zz'"):
        artifact(path, "zz", PLAIN)


def test_the_chart():
    lines = chart([0.1, 0.1, 0.3, 0.2, 0.4], width=20, height=5)
    # From the lowest score to the highest.
    assert lines[0].startswith("  0.4000 │") and lines[4].startswith("  0.1000 │")
    # The last evaluation is the highest, so it's on the top row.
    assert lines[0].rstrip().endswith("●───")
    assert lines[-1].split() == ["1", "5", "evaluations"]
    assert chart([]) == []
