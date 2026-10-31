"""
A switch picking among several jobs, defined in YAML.

Each iteration, a switch picks a job by weight: mutate the best artifact,
cross over the two best, or restart a new lineage from the seed. The job
that improves the best artifact is credited, so the report shows which jobs
pay off. Run it from the repository root:

    python examples/basics/switch_jobs/main.py
"""

import asyncio
import random
import string
from collections import Counter
from pathlib import Path

from alphatrion.swarm import Artifact, State, build_graph

TARGET = "METHINKS IT IS LIKE A WEASEL"
ALPHABET = string.ascii_uppercase + " "
rng = random.Random(5)


def mutate(content: str, edits: int) -> str:
    chars = list(content)
    for i in rng.sample(range(len(chars)), edits):
        chars[i] = rng.choice(ALPHABET)
    return "".join(chars)


def seed(state: State) -> Artifact:
    return state.commit("".join(rng.choice(ALPHABET) for _ in TARGET))


def score(state: State) -> float:
    # The current artifact, which the branch that ran committed.
    content = state.current.content
    return sum(a == b for a, b in zip(content, TARGET, strict=True)) / len(TARGET)


def pick_job(state: State, weights: dict[str, float]) -> str:
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def mutate_best(state: State) -> Artifact:
    state.checkout(state.tree.best().id)
    return state.commit(mutate(state.current.content, edits=1))


def crossover_top(state: State) -> Artifact:
    # Take each character from either of the two best artifacts, as a child
    # of the best one.
    scored = sorted(
        (a for a in state.tree if a.score is not None),
        key=lambda a: a.score,
        reverse=True,
    )
    best, other = scored[0], scored[min(1, len(scored) - 1)]
    child = "".join(
        rng.choice(pair) for pair in zip(best.content, other.content, strict=True)
    )
    state.checkout(best.id)
    return state.commit(child, metadata={"co_parent": other.id})


def restart_from_seed(state: State) -> Artifact:
    state.checkout(state.tree.root.id)
    return state.commit(mutate(state.current.content, edits=8))


def credit_job(state: State):
    # The job this iteration ran is the case the switch picked, in memory.
    job = state.memory.history(node="pick_job", last=1)[0].data["details"]
    runs = state.memory.get("runs", Counter())
    runs[job] += 1
    state.memory.set("runs", runs)
    if state.current.score > state.memory.get("best", 0.0):
        state.memory.set("best", state.current.score)
        improvements = state.memory.get("improvements", Counter())
        improvements[job] += 1
        state.memory.set("improvements", improvements)


def solved(state: State) -> bool:
    return state.tree.best().score >= 1.0


def report(state: State):
    best = state.tree.best()
    runs = state.memory.get("runs")
    improvements = state.memory.get("improvements", Counter())
    print(f"best: {best.content!r} (score {best.score:.2f})")
    for job, count in runs.most_common():
        print(f"  {job:<9} ran {count:>4} times, improved the best {improvements[job]}")


async def main():
    graph = build_graph(
        Path(__file__).parent / "pipeline.yaml",
        functions={
            "seed": seed,
            "score": score,
            "pick_job": pick_job,
            "mutate_best": mutate_best,
            "crossover_top": crossover_top,
            "restart_from_seed": restart_from_seed,
            "credit_job": credit_job,
            "solved": solved,
            "report": report,
        },
    )
    result = await graph.run()

    loop = result.state.memory.history(node="evolve")[0].data
    print(f"status: {result.status.value}, iterations: {loop['details']['iterations']}")
    if result.error:
        print(f"error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
