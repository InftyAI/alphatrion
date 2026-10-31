import json
from pathlib import Path

import pytest

from alphatrion.swarm import Files, HostStore, Tree, build_graph, tracing


def build_tree():
    tree = Tree()
    root = tree.add(
        Files(files={"p.py": "a = 1\nb = 2\n"}), metadata={"description": "seed"}
    )
    tree._set_score(root.id, 0.1)
    better = tree.add(
        Files(files={"p.py": "a = 1\nb = 3\n"}),
        parent_id=root.id,
        metadata={"description": "b is 3"},
    )
    tree._set_score(better.id, 0.5)
    tree.add(
        Files(files={"p.py": "x\n"}),
        parent_id=root.id,
        metadata={"description": "rewrite"},
    )
    return tree, root, better


def test_render_shows_the_code_tree():
    tree, root, better = build_tree()
    lines = tree.render().splitlines()
    assert lines[0] == f"{root.id[:8]}  0.1000  seed"
    assert lines[1] == f"├── {better.id[:8]}  0.5000  b is 3 ★  +1 -1"
    assert lines[2].startswith("└── ") and "unscored  rewrite  +1 -2" in lines[2]


def test_diff_against_the_parent():
    tree, root, better = build_tree()
    assert tree.diff(better.id).splitlines()[2:] == [
        "@@ -1,2 +1,2 @@",
        " a = 1",
        "-b = 2",
        "+b = 3",
    ]
    # The root adds everything.
    assert "+a = 1" in tree.diff(root.id)


def propose(state) -> Files:
    code = state.current.content.files["p.py"] if state.current else "n = 0\n"
    n = int(code.split("=")[1]) + 1
    files = Files(files={"p.py": f"n = {n}\n"})
    state.commit(files, metadata={"description": f"n is {n}"})
    return files


def score(state, program: Files) -> float:
    return float(program.files["p.py"].split("=")[1])


def counting(iterations: int = 3):
    return build_graph(
        {
            "name": "count",
            "inputs": ["data"],
            "nodes": [
                {
                    "name": "improve",
                    "type": "loop",
                    "max_iters": iterations,
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
            ],
        }
    )


def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


@pytest.mark.asyncio
async def test_an_experiment_keeps_its_runs(tmp_path):
    data = tmp_path / "data.txt"
    data.write_text("a dataset")
    store = HostStore(tmp_path / "experiments", experiment="count", checkpoint_every=2)
    tracing.setup(store.spans())
    try:
        result = await counting().run(inputs={"data": str(data)}, store=store)
    finally:
        tracing.setup()
    assert result.status.value == "completed", result.error

    experiment = tmp_path / "experiments" / "count"
    (run,) = store.runs()
    assert run["status"] == "completed" and run["pipeline"] == "count"
    # The dataset is fingerprinted, not copied.
    assert run["inputs"]["data"]["bytes"] == 9
    assert len(run["inputs"]["data"]["sha256"]) == 64
    run_dir = experiment / "runs" / run["id"]
    assert "propose" in (run_dir / "pipeline.txt").read_text()
    # The run's spans are in its directory.
    assert any(s["name"] == "node evaluate" for s in lines(run_dir / "traces.jsonl"))

    # The experiment's artifacts, each with its files, its diff, and where
    # it was made.
    last = result.state.current
    assert (experiment / "artifacts" / last.id / "p.py").read_text() == "n = 3\n"
    assert "+n = 3" in (experiment / "artifacts" / last.id / "diff.patch").read_text()
    assert last.run == run["id"] and last.iteration == {"improve": 3}
    # Every evaluation, with its run and iteration, e.g. to plot.
    metrics = lines(experiment / "metrics.jsonl")
    assert [(m["iteration"]["improve"], m["score"]) for m in metrics] == [
        (1, 1.0),
        (2, 2.0),
        (3, 3.0),
    ]
    assert {m["run"] for m in metrics} == {run["id"]}
    assert "n is 3 ★" in (experiment / "tree.txt").read_text()


@pytest.mark.asyncio
async def test_a_second_run_continues_the_experiment(tmp_path):
    data = tmp_path / "data.txt"
    data.write_text("a dataset")
    store = HostStore(tmp_path / "experiments", experiment="count")
    await counting(2).run(inputs={"data": str(data)}, store=store)
    # Continued from where the first run ended, as another run.
    state = store.load()
    assert state.tree.best().score == 2.0
    result = await counting(2).run(state=state, inputs={"data": str(data)}, store=store)
    assert result.state.tree.best().score == 4.0

    first, second = store.runs()
    metrics = lines(tmp_path / "experiments" / "count" / "metrics.jsonl")
    assert [(m["run"], m["score"]) for m in metrics] == [
        (first["id"], 1.0),
        (first["id"], 2.0),
        (second["id"], 3.0),
        (second["id"], 4.0),
    ]
    assert len(store.load().tree) == 4


@pytest.mark.asyncio
async def test_checkpoints_and_parents(tmp_path):
    data = tmp_path / "data.txt"
    data.write_text("a dataset")
    parent = {"experiment": "count-meta", "run": "r1", "artifact": "a1"}
    store = HostStore(
        tmp_path / "experiments", experiment="count", parent=parent, checkpoint_every=2
    )

    seen = []

    def check(state, loop, iteration):
        # After iteration 2, the checkpoint has its artifacts.
        if iteration == 2:
            seen.append(len(HostStore(tmp_path / "experiments", "count").load().tree))

    original = store.iteration
    store.iteration = lambda state, loop, iteration: (
        original(state, loop, iteration),
        check(state, loop, iteration),
    )
    await counting(3).run(inputs={"data": str(data)}, store=store)
    assert seen == [2]
    assert store.runs()[0]["parent"] == parent


def test_artifact_formats_survive_saving(tmp_path):
    tree, root, better = build_tree()
    tree.save(tmp_path / "tree.json")
    loaded = Tree.load(tmp_path / "tree.json")
    assert isinstance(loaded.get(better.id).content, Files)
    assert loaded.get(better.id).content == better.content
    assert loaded.diff(better.id) == tree.diff(better.id)


@pytest.mark.asyncio
async def test_a_dataset_directory_is_fingerprinted_without_the_store(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "trace.json").write_text("{}")
    # The experiments are kept inside the dataset's directory.
    store = HostStore(data / "experiments", experiment="count")
    await counting(1).run(inputs={"data": str(data)}, store=store)
    await counting(1).run(state=store.load(), inputs={"data": str(data)}, store=store)
    files = store.runs()[-1]["inputs"]["data"]["files"]
    assert [Path(f["path"]).name for f in files] == ["trace.json"]
