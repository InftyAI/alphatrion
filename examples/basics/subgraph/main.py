"""
A subgraph: the pipeline repeats an attempt until solved, and attempt.yaml
details what one attempt does, as a subgraph node referencing that file.

The artifact is a string evolving toward a target sentence, a stand-in for
a prompt or a program that a model would improve. Run it from the
repository root:

    python examples/basics/subgraph/main.py
"""

import asyncio
import random
import string
from collections import Counter
from pathlib import Path

from alphatrion.swarm import Artifact, State, build_graph

TARGET = "METHINKS IT IS LIKE A WEASEL"
ALPHABET = string.ascii_uppercase + " "
rng = random.Random(42)


def seed(state: State) -> Artifact:
    return state.commit("".join(rng.choice(ALPHABET) for _ in TARGET))


def propose(state: State) -> Artifact:
    # Mutate one character of the best artifact so far.
    state.checkout(state.tree.best().id)
    parent = state.current.content
    i = rng.randrange(len(parent))
    return state.commit(parent[:i] + rng.choice(ALPHABET) + parent[i + 1 :])


def not_duplicate(state: State, artifact: Artifact):
    parent = state.tree.parent(artifact.id)
    return artifact.content != parent.content, "same as its parent"


def score(state: State, artifact: Artifact) -> float:
    return sum(a == b for a, b in zip(artifact.content, TARGET, strict=True)) / len(
        TARGET
    )


def solved(state: State) -> bool:
    return state.tree.best().score >= 1.0


async def main():
    graph = build_graph(
        Path(__file__).parent / "pipeline.yaml",
        functions={
            "seed": seed,
            "propose": propose,
            "not_duplicate": not_duplicate,
            "score": score,
            "solved": solved,
        },
    )
    result = await graph.run()

    state = result.state
    best = state.tree.best()
    print(f"best: {best.content!r} (score {best.score:.2f})")
    # The subgraph's nodes are recorded under its name.
    runs = Counter(entry.node for entry in state.memory)
    for node in ("attempt.propose", "attempt.guard", "attempt.evaluate", "attempt"):
        print(f"  {node:<17} ran {runs[node]} times")
    rejected = sum(
        entry.data["choice"] == "fail"
        for entry in state.memory.history(node="attempt.guard")
    )
    print(f"  duplicates rejected before evaluation: {rejected}")
    print(f"status: {result.status.value}")
    if result.error:
        print(f"error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
