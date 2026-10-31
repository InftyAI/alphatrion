"""
An experiment in the terminal, as a HostStore kept it: its best score, a
chart of every evaluation and the best so far, and the tree of artifacts,
or one artifact's metrics and diff:

    python -m alphatrion.swarm.show ~/eplb/experiments/eplb
    python -m alphatrion.swarm.show ~/eplb/experiments/eplb 16035fde

It reads what the experiment has checkpointed, so it works while a run is
going too.
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from alphatrion.swarm.tree import Tree

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
GREEN, RED, CYAN = "\033[32m", "\033[31m", "\033[36m"


class Style:
    """ANSI styles, when writing to a terminal."""

    def __init__(self, enabled: bool):
        self.enabled = enabled

    def __call__(self, text: str, *codes: str) -> str:
        return "".join(codes) + text + RESET if self.enabled and codes else text


def _lines(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def _runs(path: Path) -> list[dict[str, Any]]:
    runs = [
        json.loads((r / "run.json").read_text())
        for r in (path / "runs").glob("*")
        if (r / "run.json").exists()
    ]
    return sorted(runs, key=lambda run: run["started_at"])


def chart(scores: list[float], width: int = 64, height: int = 12) -> list[str]:
    """Every evaluation as a dot, and the best so far as a line, on one
    axis from the lowest score to the highest, so small gains show. Each
    evaluation gets a share of the width, and past width evaluations each
    column shows the last of its share."""
    if not scores:
        return []
    best, running = [], float("-inf")
    for score in scores:
        running = max(running, score)
        best.append(running)
    if len(scores) <= width:
        step = max(1, min(6, width // len(scores)))
        columns, at = len(scores) * step, [i * step for i in range(len(scores))]
        index = [min(c // step, len(scores) - 1) for c in range(columns)]
    else:
        columns, at = width, None
        index = [round(c * (len(scores) - 1) / (width - 1)) for c in range(width)]
    lo, hi = min(scores), max(scores)
    if hi == lo:
        lo, hi = lo - 0.5, hi + 0.5

    def row(v: float) -> int:
        return round((v - lo) / (hi - lo) * (height - 1))

    grid = [[" "] * columns for _ in range(height)]
    # The best so far, a line under the dots.
    for c in range(columns):
        grid[row(best[index[c]])][c] = "─"
    dots = at if at is not None else range(columns)
    for c in dots:
        grid[row(scores[index[c]])][c] = "●"
    lines = []
    for r in range(height - 1, -1, -1):
        label = (
            f"{lo + (hi - lo) * r / (height - 1):.4f}" if r in (0, height - 1) else ""
        )
        lines.append(f"{label:>8} │" + "".join(grid[r]))
    lines.append(" " * 9 + "└" + "─" * columns)
    lines.append(
        " " * 10 + "1" + str(len(scores)).rjust(max(columns - 1, 1)) + "  evaluations"
    )
    return lines


def overview(path: Path, style: Style) -> str:
    info = json.loads((path / "experiment.json").read_text())
    tree = Tree.load(path / "tree.json") if (path / "tree.json").exists() else Tree()
    metrics = _lines(path / "metrics.jsonl")
    runs = _runs(path)
    models: Counter = Counter()
    for run in runs:
        for request in _lines(path / "runs" / run["id"] / "requests.jsonl"):
            models[request["model"]] += 1

    out = [style(f"Experiment {info['name']}", BOLD), ""]
    best = tree.best()
    if best is not None:
        out.append(
            f"best score  {style(f'{best.score:.4f}', BOLD)}  {best.id[:8]}  {best.metadata.get('description', '')}"
        )
    scored = sum(1 for a in tree if a.score is not None)
    out.append(f"programs    {len(tree)} ({scored} scored), {len(metrics)} evaluations")
    last = f", the last {runs[-1]['status']}" if runs else ""
    out.append(f"runs        {len(runs)}{last}")
    if models:
        counts = ", ".join(f"{model} {count}" for model, count in models.most_common())
        out.append(f"requests    {sum(models.values())}: {counts}")

    if metrics:
        out += [
            "",
            style("Score over evaluations", BOLD)
            + style("  ● an evaluation  ─ the best so far", DIM),
        ]
        out += chart([m["score"] for m in metrics])
    if len(tree):
        out += [
            "",
            style("Tree of programs", BOLD)
            + style("  each under the one it was edited from", DIM),
        ]
        out.append(tree.render())
    return "\n".join(out)


def artifact(path: Path, prefix: str, style: Style) -> str:
    tree = Tree.load(path / "tree.json")
    matches = [a for a in tree if a.id.startswith(prefix)]
    if len(matches) != 1:
        raise SystemExit(
            f"{len(matches) or 'No'} artifacts start with {prefix!r}"
            + (f": {', '.join(a.id[:12] for a in matches)}" if matches else "")
        )
    a = matches[0]
    score = "unscored" if a.score is None else f"{a.score:.4f}"
    out = [
        style(f"Program {a.id[:8]}", BOLD) + f"  {score}",
        a.metadata.get("description", ""),
        "",
    ]
    metrics = [m for m in _lines(path / "metrics.jsonl") if m["artifact_id"] == a.id]
    if metrics:
        for key, value in metrics[-1]["values"].items():
            out.append(f"{key:<20} {value:.4f}")
    parent = tree.parent(a.id)
    where = ", ".join(f"{loop} {i}" for loop, i in a.iteration.items()) or "-"
    for key, value in (
        ("parent", parent.id[:8] if parent else "the root"),
        ("run", a.run or "-"),
        ("iteration", where),
        ("model", a.metadata.get("model") or "-"),
        ("request", a.metadata.get("request") or "-"),
        ("files", str(path / "artifacts" / a.id)),
    ):
        out.append(f"{key:<20} {value}")
    diff = tree.diff(a.id)
    if diff:
        out += ["", style("Change from its parent", BOLD)]
        for line in diff.splitlines():
            if line.startswith("@@"):
                out.append(style(line, CYAN))
            elif line.startswith("+") and not line.startswith("+++"):
                out.append(style(line, GREEN))
            elif line.startswith("-") and not line.startswith("---"):
                out.append(style(line, RED))
            else:
                out.append(line)
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description="An experiment in the terminal.")
    parser.add_argument(
        "experiment", help="its directory, e.g. ~/eplb/experiments/eplb"
    )
    parser.add_argument(
        "artifact", nargs="?", help="an artifact's id, or its start, to show"
    )
    args = parser.parse_args()
    path = Path(args.experiment).expanduser()
    if not (path / "experiment.json").exists():
        raise SystemExit(f"{path} isn't an experiment: it has no experiment.json")
    style = Style(sys.stdout.isatty())
    print(
        artifact(path, args.artifact, style) if args.artifact else overview(path, style)
    )


if __name__ == "__main__":
    main()
