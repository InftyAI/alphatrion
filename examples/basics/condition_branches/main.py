"""
Conditions and branches, defined in YAML.

Each iteration, a condition checks whether progress has stalled, and picks a
branch: while it improves, exploit makes a small edit to the best artifact,
and once it stalls, explore jumps back to a random earlier artifact and
makes several edits. Another condition breaks the loop once the target is
reached. Run it from the repository root:

    python examples/basics/condition_branches/main.py
"""

import asyncio
import random
import string
from pathlib import Path

from alphatrion.swarm import Artifact, State, build_graph

TARGET = "METHINKS IT IS LIKE A WEASEL"
ALPHABET = string.ascii_uppercase + " "
rng = random.Random(3)


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


def stalled(state: State, patience: int) -> bool:
    # The number of iterations since the best score last improved. A
    # condition only decides, so the explore branch resets it.
    return state.memory.get("stalled", 0) >= patience


def mutate_best(state: State) -> Artifact:
    state.checkout(state.tree.best().id)
    return state.commit(mutate(state.current.content, edits=1))


def jump_from_ancestor(state: State) -> Artifact:
    state.memory.set("stalled", 0)
    lineage = state.tree.lineage(state.tree.best().id)
    state.checkout(rng.choice(lineage).id)
    return state.commit(mutate(state.current.content, edits=3))


def track_progress(state: State):
    best = state.tree.best().score
    if best > state.memory.get("best", 0.0):
        state.memory.set("best", best)
        state.memory.set("stalled", 0)
    else:
        state.memory.set("stalled", state.memory.get("stalled", 0) + 1)


def solved(state: State) -> bool:
    return state.tree.best().score >= 1.0


def report(state: State):
    best = state.tree.best()
    exploits = len(state.memory.history(node="mutate"))
    explores = len(state.memory.history(node="jump"))
    print(f"best: {best.content!r} (score {best.score:.2f})")
    print(
        f"iterations: {exploits + explores}, exploit: {exploits}, explore: {explores}"
    )


async def main():
    graph = build_graph(
        Path(__file__).parent / "pipeline.yaml",
        functions={
            "seed": seed,
            "score": score,
            "stalled": stalled,
            "mutate_best": mutate_best,
            "jump_from_ancestor": jump_from_ancestor,
            "track_progress": track_progress,
            "solved": solved,
            "report": report,
        },
    )
    result = await graph.run()

    loop = result.state.memory.history(node="search")[0].data
    print(f"status: {result.status.value}, loop ended by: {loop['choice']}")
    if result.error:
        print(f"error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
