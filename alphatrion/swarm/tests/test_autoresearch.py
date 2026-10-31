"""Run the autoresearch example's pipeline and functions on a tiny CPU
training script, with a scripted model, so the loop is tested without a GPU
or API keys."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from alphatrion.swarm import ModelResponse, ScoreMode, State, build_graph
from alphatrion.swarm.nodes import Candidate
from alphatrion.swarm.pipeline import load_pipeline

EXAMPLE = Path(__file__).parents[3] / "examples" / "cases" / "autoresearch"
sys.path.insert(0, str(EXAMPLE))

import autoresearch  # noqa: E402


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
def repo(tmp_path):
    shutil.copy(Path(__file__).parent / "autoresearch_toy" / "train.py", tmp_path)
    for args in (["init", "-q"], ["add", "."], ["commit", "-qm", "baseline"]):
        subprocess.run(["git", *autoresearch.AUTHOR, *args], cwd=tmp_path, check=True)
    return tmp_path


@pytest.mark.asyncio
async def test_autoresearch(repo):
    model = ScriptedModel(
        [
            edit("STEPS = 300", "STEPS = 400", "more steps"),  # improves
            edit("DEGREE = 3", "DEGREE = 2", "lower degree"),  # worse
            edit("LR = 0.05", "LR = 5.0", "huge lr"),  # diverges
            "I would try a larger model.",  # no edits, nothing tried
            edit("LR = 0.05", "LR = 0.15", "higher lr"),  # improves
        ]
    )
    pipeline = load_pipeline(EXAMPLE / "pipeline.yaml")
    top = {node.name: node for node in pipeline.nodes}
    research = top["research"]
    nodes = {node.name: node for node in research.nodes}
    pipeline.params["command"] = f"{sys.executable} train.py"
    research.max_iters = 5
    nodes["propose"].candidates = [Candidate(model="scripted", provider="model")]

    graph = build_graph(pipeline, functions={**autoresearch.FUNCTIONS, "model": model})
    state = State()
    result = await graph.run(
        state=state,
        inputs={"workdir": str(repo), "instructions": str(EXAMPLE / "proposer.md")},
    )
    assert result.status.value == "completed", result.error

    rows = [
        line.split("\t") for line in (repo / "results.tsv").read_text().splitlines()
    ]
    assert [(row[3], row[4]) for row in rows[1:]] == [
        ("keep", "baseline"),
        ("keep", "more steps"),
        ("discard", "lower degree"),
        ("crash", "huge lr"),
        ("keep", "higher lr"),
    ]
    # Only the kept experiments remain in git, and train.py has both of them.
    log = subprocess.run(
        ["git", "log", "--format=%s"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("\n")
    assert log[:3] == ["higher lr", "more steps", "baseline"]
    code = (repo / "train.py").read_text()
    assert "STEPS = 400" in code and "LR = 0.15" in code
    # results.tsv stays untracked.
    status = subprocess.run(
        ["git", "status", "--porcelain"],
        check=False,
        cwd=repo,
        capture_output=True,
        text=True,
    ).stdout
    assert status == ""

    # The tree mirrors git: every experiment tried, and the best is current.
    best = state.tree.best(ScoreMode.MIN)
    assert best.metadata["description"] == "higher lr"
    assert state.current.id == best.id
    # The model saw the results so far in each prompt.
    assert "huge lr" in model.requests[-1].messages[0]["content"]
