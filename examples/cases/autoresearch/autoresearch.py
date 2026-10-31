"""
The node functions of the autoresearch pipeline, after
https://github.com/karpathy/autoresearch: a model edits train.py, it trains
for the fixed 5-minute budget, and the edit is kept if val_bpb improved,
else reverted.

The pipeline has the stages of the research loop, and each stage does its
details here. Git does the real keeping and reverting in the repo, and the
tree mirrors it, so the lineage of every experiment and its score stays
queryable. The repo and the model's instructions are the pipeline's
inputs, workdir and instructions.
"""

import re
import subprocess
from pathlib import Path

from alphatrion.swarm import (
    Choice,
    Execution,
    Files,
    Metrics,
    ModelRequest,
    ModelResponse,
    State,
)

TRAIN = "train.py"
RESULTS = "results.tsv"
HEADER = "commit\tval_bpb\tmemory_gb\tstatus\tdescription\n"
# Commits are made by the agent, without touching the repo's git config.
AUTHOR = ["-c", "user.name=autoresearch", "-c", "user.email=autoresearch@localhost"]


def git(workdir: str, *args: str) -> str:
    return subprocess.run(
        ["git", *AUTHOR, *args],
        cwd=workdir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def log_result(
    state: State, workdir: str, metrics: Metrics | None, status: str
) -> None:
    val_bpb = metrics.score if metrics else 0.0
    memory_gb = metrics.values.get("peak_vram_mb", 0.0) / 1024 if metrics else 0.0
    description = state.current.metadata.get("description", "baseline")
    commit = state.current.metadata.get("commit", "")
    with open(Path(workdir) / RESULTS, "a") as f:
        f.write(f"{commit}\t{val_bpb:.6f}\t{memory_gb:.1f}\t{status}\t{description}\n")


async def baseline(
    state: State, workdir: str, command: str, train_timeout: float
) -> Execution:
    """Start results.tsv, untracked by git, commit the current train.py as
    the root artifact every experiment is compared with, and train it once.
    A crashed baseline ends the step on the crashed choice."""
    repo = Path(workdir)
    (repo / RESULTS).write_text(HEADER)
    exclude = repo / ".git" / "info" / "exclude"
    exclude.parent.mkdir(exist_ok=True)
    existing = exclude.read_text() if exclude.exists() else ""
    if RESULTS not in existing.split():
        exclude.write_text(existing + f"\n{RESULTS}\n")

    code = Files(files={TRAIN: (repo / TRAIN).read_text()})
    state.commit(
        code, metadata={"commit": git(workdir, "rev-parse", "--short", "HEAD")}
    )
    run = await train(state, command, train_timeout)
    if crashed(run):
        raise Choice("crashed", run.stderr[-2000:])
    log_result(state, workdir, measure(state, run), "keep")
    return run


def prompt(state: State, instructions: str, workdir: str) -> ModelRequest:
    """Ask for one experiment: the research program as the system prompt,
    and the current train.py with the results so far."""
    code = state.current.content
    results = (Path(workdir) / RESULTS).read_text()
    return ModelRequest(
        system=Path(instructions).read_text(),
        messages=[
            {
                "role": "user",
                "content": (
                    f"The current {TRAIN}:\n\n```python\n{code.files[TRAIN]}```\n\n"
                    f"The results so far, in {RESULTS}:\n\n{results}\n"
                    "Propose the next experiment."
                ),
            }
        ],
    )


async def experiment(
    state: State,
    reply: ModelResponse,
    workdir: str,
    command: str,
    train_timeout: float,
) -> Execution:
    """Run one experiment: apply the reply's edits to train.py, commit them
    as a new artifact, and train. A reply whose edits don't each match
    train.py exactly once is skipped, as nothing is tried, and a run that
    crashes is logged and reverted, ending the step on the crashed choice."""
    code = state.current.content.files[TRAIN]
    edits = EDIT.findall(reply.text)
    if not edits or any(code.count(search) != 1 for search, _ in edits):
        raise Choice(
            "skip",
            "the reply has no edits matching train.py exactly once",
        )
    for search, replace in edits:
        code = code.replace(search, replace, 1)
    match = re.search(r"^Description:\s*(.+)$", reply.text, re.M)
    description = match.group(1).strip() if match else "no description"

    (Path(workdir) / TRAIN).write_text(code)
    git(workdir, "commit", "-qam", description)
    commit = git(workdir, "rev-parse", "--short", "HEAD")
    state.commit(
        Files(files={TRAIN: code}, metadata={"model": reply.model}),
        metadata={
            "commit": commit,
            "description": description,
            "request": reply.metadata.get("request"),
        },
    )
    run = await train(state, command, train_timeout)
    if crashed(run):
        log_result(state, workdir, None, "crash")
        revert(state, workdir)
        raise Choice("crashed", run.stderr[-2000:])
    return run


def measure(state: State, run: Execution) -> Metrics:
    """The evaluator: val_bpb, lower is better, and the peak memory."""
    values = {
        key: float(value)
        for key, value in re.findall(
            r"^(val_bpb|peak_vram_mb):\s*(\S+)", run.stdout, re.M
        )
    }
    return Metrics(values=values, primary="val_bpb", lower_is_better=True)


def settle(state: State, metrics: Metrics, workdir: str) -> Files:
    """Keep the experiment if its val_bpb, scored by the evaluator, is lower
    than that of the train.py it started from, else discard and revert it.
    Returns the train.py the next experiment starts from."""
    if metrics.score < state.tree.parent(state.current.id).score:
        log_result(state, workdir, metrics, "keep")
        return state.current.content
    log_result(state, workdir, metrics, "discard")
    return revert(state, workdir)


async def train(state: State, command: str, train_timeout: float) -> Execution:
    """Run the training command on the repo, mounted at /repo in the node's
    runtime, killing it and everything it started after train_timeout
    seconds."""
    return await state.runtime.exec(
        "sh", ["-c", command], cwd="/repo", timeout=train_timeout
    )


def crashed(run: Execution) -> bool:
    return not run.succeeded or re.search(r"^val_bpb:", run.stdout, re.M) is None


EDIT = re.compile(r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE", re.S)


def revert(state: State, workdir: str) -> Files:
    """Undo the last experiment, in git and in the tree, and return the
    train.py before it."""
    git(workdir, "reset", "-q", "--hard", "HEAD~1")
    return state.checkout(state.tree.parent(state.current.id).id).content


FUNCTIONS = {fn.__name__: fn for fn in (baseline, prompt, experiment, measure, settle)}
