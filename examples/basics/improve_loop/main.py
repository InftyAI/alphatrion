"""
An improvement loop defined in YAML.

The artifact is a string evolving toward a target sentence, a stand-in for a
prompt or a program improved by an LLM. Run it from the repository root:

    python examples/basics/improve_loop/main.py
"""

import asyncio
import random
import string
from pathlib import Path

from alphatrion.swarm import Artifact, State, build_graph

TARGET = "METHINKS IT IS LIKE A WEASEL"
ALPHABET = string.ascii_uppercase + " "
rng = random.Random(42)


def seed(state: State) -> Artifact:
    return state.commit("".join(rng.choice(ALPHABET) for _ in TARGET))


def propose(state: State) -> Artifact:
    # Improve on the best artifact so far, so a worse variant is never a parent.
    best = state.tree.best()
    if best is not None:
        state.checkout(best.id)
    # Mutate one character, a stand-in for an LLM proposing an edit.
    parent = state.current.content
    i = rng.randrange(len(parent))
    return state.commit(parent[:i] + rng.choice(ALPHABET) + parent[i + 1 :])


def not_duplicate(state: State):
    parent = state.tree.parent(state.current.id)
    return state.current.content != parent.content, "same as its parent"


def score(state: State, artifact: Artifact) -> float:
    return sum(a == b for a, b in zip(artifact.content, TARGET, strict=True)) / len(
        TARGET
    )


def good_enough(state: State, target: float) -> bool:
    best = state.tree.best()
    return best is not None and best.score >= target


async def main():
    graph = build_graph(
        Path(__file__).parent / "pipeline.yaml",
        functions={
            "seed": seed,
            "propose": propose,
            "not_duplicate": not_duplicate,
            "score": score,
            "good_enough": good_enough,
        },
    )
    result = await graph.run()

    state = result.state
    best = state.tree.best()
    lineage = state.tree.lineage(best.id)
    loop = state.memory.history(node="improve")[0].data["details"]
    rejected = sum(
        e.data["choice"] == "fail" for e in state.memory.history(node="guard")
    )
    print(f"status: {result.status.value}, iterations: {loop['iterations']}")
    print(f"artifacts: {len(state.tree)}, rejected duplicates: {rejected}")
    print(f"best: {best.content!r} (score {best.score:.2f})")
    print("lineage of the best, from the root:")
    # Show how the best artifact evolved, sampled along its lineage.
    step = max(1, len(lineage) // 8)
    for artifact in lineage[:-1:step] + [lineage[-1]]:
        shown = "-" if artifact.score is None else f"{artifact.score:.2f}"
        print(f"  {artifact.content}  {shown}")


if __name__ == "__main__":
    asyncio.run(main())
