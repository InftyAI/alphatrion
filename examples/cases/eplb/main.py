"""
Evolve the EPLB algorithm of ADRS's eplb example on CPU. See README.md for
the setup. Then, from the repository root, with the directory holding
expert-load.json:

    python examples/cases/eplb/main.py ~/eplb
"""

import asyncio
import logging
import sys
from pathlib import Path

from alphatrion.swarm import HostStore, ScoreMode, build_graph, tracing

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from eplb import FUNCTIONS  # noqa: E402


async def main(data: str):
    # A line for each step as it runs: a model's reply can take a minute.
    logging.basicConfig(format="%(message)s")
    logging.getLogger("alphatrion.swarm").setLevel(logging.INFO)
    graph = build_graph(HERE / "pipeline.yaml", functions=FUNCTIONS)
    # The experiment, next to the data: each run of it continues the last,
    # with its artifacts, metrics, requests and traces kept.
    store = HostStore(Path(data) / "experiments", experiment="eplb", checkpoint_every=1)
    tracing.setup(store.spans())
    state = store.load()
    result = await graph.run(
        state=state,
        inputs={"data": data, "instructions": str(HERE / "proposer.md")},
        store=store,
    )

    # Every program, under the one it was edited from, with its score.
    print(state.tree.render())
    best = state.tree.best(ScoreMode.MAX)
    if best is not None:
        print(f"best: {best.score:.4f} ({best.metadata['description']})")
    print(f"requests: {dict(state.requests.counts())}, kept in {store.path}")
    print(
        f"to see it again, or a program: python -m alphatrion.swarm.show {store.path} [id]"
    )
    print(f"status: {result.status.value}")
    if result.error:
        print(f"error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main(str(Path(sys.argv[1]).expanduser().resolve())))
