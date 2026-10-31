"""
Run autoresearch (https://github.com/karpathy/autoresearch) as a pipeline,
on a GPU machine, e.g. an H100. See README.md for the setup. Then, from the
repository root:

    python examples/cases/autoresearch/main.py --repo ~/autoresearch

It runs until stopped with Ctrl-C, like autoresearch, or for --iterations
experiments. Each experiment is a commit on an autoresearch/<tag> branch of
the repo, and results.tsv in the repo logs them all.
"""

import argparse
import asyncio
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from alphatrion.swarm import ScoreMode, State, build_graph
from alphatrion.swarm.pipeline import load_pipeline

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))

from autoresearch import FUNCTIONS  # noqa: E402


def find(nodes, name):
    """Find a node by name, nested ones included."""
    for node in nodes:
        if node.name == name:
            return node
        children = [*getattr(node, "nodes", []), *sum(node.branches.values(), [])]
        found = find(children, name)
        if found is not None:
            return found
    return None


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo", required=True, help="a checkout of karpathy/autoresearch"
    )
    parser.add_argument("--tag", default=datetime.now().strftime("%b%d").lower())
    parser.add_argument(
        "--iterations", type=int, default=0, help="0 runs until stopped"
    )
    parser.add_argument("--program", default=str(HERE / "proposer.md"))
    parser.add_argument("--pipeline", default=str(HERE / "pipeline.yaml"))
    args = parser.parse_args()

    repo = Path(args.repo).expanduser().resolve()
    if not (repo / "train.py").exists() or not (repo / ".git").exists():
        raise SystemExit(f"{repo} is not a git checkout of autoresearch")
    # Like autoresearch, experiment on a branch of its own.
    subprocess.run(
        ["git", "checkout", "-qb", f"autoresearch/{args.tag}"], cwd=repo, check=True
    )

    pipeline = load_pipeline(args.pipeline)
    find(pipeline.nodes, "research").max_iters = args.iterations or None
    graph = build_graph(pipeline, functions=FUNCTIONS)
    # The state is created here, so the results are still at hand when the
    # run is stopped with Ctrl-C.
    state = State()
    inputs = {"workdir": str(repo), "instructions": args.program}
    try:
        result = await graph.run(state=state, inputs=inputs)
    except asyncio.CancelledError:
        result = None

    print((repo / "results.tsv").read_text(), end="")
    best = state.tree.best(ScoreMode.MIN)
    if best is None:
        return
    print(
        f"best val_bpb: {best.score:.6f} ({best.metadata.get('description', 'baseline')})"
    )
    print(f"status: {result.status.value if result else 'stopped'}")
    if result is not None and result.error:
        print(f"error: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
