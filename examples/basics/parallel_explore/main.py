"""
Parallel explorers, defined in code with the node classes.

Four explorers start from the same seed and each evolves its own lineage in
the shared tree, backtracking when a variant is worse. Once every explorer
reaches the target score, the best artifact among them is kept. Run it from
the repository root:

    python examples/basics/parallel_explore/main.py
"""

import asyncio
import random
import string

from alphatrion.swarm import (
    ActionNode,
    Artifact,
    EvaluatorNode,
    LoopNode,
    ParallelNode,
    Pipeline,
    State,
    build_graph,
)

TARGET = "METHINKS IT IS LIKE A WEASEL"
ALPHABET = string.ascii_uppercase + " "
rng = random.Random(7)


def seed(state: State) -> Artifact:
    return state.commit("".join(rng.choice(ALPHABET) for _ in TARGET))


def propose(state: State) -> Artifact:
    # Each explorer mutates its own current artifact, not the global best,
    # so the explorers search independently.
    parent = state.current.content
    i = rng.randrange(len(parent))
    return state.commit(parent[:i] + rng.choice(ALPHABET) + parent[i + 1 :])


def score(state: State, artifact: Artifact) -> float:
    return sum(a == b for a, b in zip(artifact.content, TARGET, strict=True)) / len(
        TARGET
    )


def keep_or_backtrack(state: State):
    # Go back to the parent when the variant is worse, so the next proposal
    # branches from it instead.
    parent = state.tree.parent(state.current.id)
    if parent.score is not None and state.current.score < parent.score:
        state.checkout(parent.id)


def reached(state: State, target: float) -> bool:
    return state.current.score is not None and state.current.score >= target


def subtree(state: State, artifact) -> list:
    """The artifact and all its descendants."""
    nodes, pending = [], [artifact]
    while pending:
        node = pending.pop()
        nodes.append(node)
        pending += state.tree.children(node.id)
    return nodes


def report(state: State):
    best = state.current
    print(f"best: {best.content!r} (score {best.score:.2f})")
    # Each explorer's first variant is a child of the seed, and its
    # lineage grows below it.
    for child in state.tree.children(state.tree.root.id):
        lineage = [a for a in subtree(state, child) if a.score is not None]
        top = max(lineage, key=lambda a: a.score)
        print(
            f"  explorer starting with {child.content!r}: "
            f"{len(lineage)} artifacts, best {top.score:.2f}"
        )


async def main():
    pipeline = Pipeline(
        name="parallel-explore",
        nodes=[
            ActionNode(name="seed", fn=seed),
            # The seed is evaluated, so explorers can backtrack to it.
            EvaluatorNode(
                name="evaluate_seed",
                fn=score,
                params={"artifact": "${nodes.seed.output}"},
            ),
            ParallelNode(
                name="explore",
                n=4,
                join="best",
                nodes=[
                    LoopNode(
                        name="explorer",
                        max_iters=2000,
                        until=reached,
                        params={"target": 0.7},
                        nodes=[
                            ActionNode(name="propose", fn=propose),
                            EvaluatorNode(
                                name="evaluate",
                                fn=score,
                                params={"artifact": "${nodes.propose.output}"},
                            ),
                            ActionNode(
                                name="keep_or_backtrack",
                                fn=keep_or_backtrack,
                            ),
                        ],
                    )
                ],
            ),
            ActionNode(name="report", fn=report),
        ],
    )
    result = await build_graph(pipeline).run()

    state = result.state
    print(f"status: {result.status.value}, artifacts: {len(state.tree)}")
    if result.error:
        print(f"error: {result.error}")
    for entry in state.memory.history(node="explorer"):
        print(
            f"  {entry.data['branch']}: {entry.data['details']['iterations']} iterations"
        )


if __name__ == "__main__":
    asyncio.run(main())
