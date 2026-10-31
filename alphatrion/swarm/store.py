"""
Where experiments are kept. An experiment is a goal and its judge, improved
over runs: it owns the tree of artifacts, the memory, and every
evaluation's metrics. A run is one execution of a pipeline on it, owning its
status, inputs, the pipeline it ran, its model requests and its traces.
Anything finer, a loop's iteration or a parallel branch, is an index on
what's recorded, not a level, as in MLflow's steps or OpenEvolve's
iterations.

A store is given to graph.run(store=...), which records into it as the run
happens: artifacts when committed, metrics when evaluated, requests when
sent, checkpoints as loops iterate, and the rest when it ends, so a crashed
run keeps what it reached.
"""

import hashlib
import json
import uuid
from abc import ABC, abstractmethod
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult

from alphatrion.swarm.context import current_iterations
from alphatrion.swarm.formats import Files, Metrics
from alphatrion.swarm.memory import Memory
from alphatrion.swarm.requests import RequestRecord
from alphatrion.swarm.tracing import span_record
from alphatrion.swarm.tree import Artifact, Tree

if TYPE_CHECKING:
    from alphatrion.swarm.graph import Graph, GraphResult
    from alphatrion.swarm.state import State


class RunStore(ABC):
    """Keeps an experiment's runs. Custom stores, e.g. for a database,
    subclass it."""

    # The id of the run being kept, None between runs.
    run_id: str | None = None

    @abstractmethod
    def start(self, graph: "Graph", inputs: dict[str, Any]) -> str:
        """Start keeping a run, returning its id."""

    @abstractmethod
    def artifact(self, artifact: Artifact, tree: Tree | None = None) -> None:
        """An artifact was committed, in the tree."""

    @abstractmethod
    def metrics(
        self, state: "State", node: str, artifact_id: str, metrics: Metrics
    ) -> None:
        """An evaluator measured an artifact."""

    @abstractmethod
    def request(self, record: RequestRecord) -> None:
        """A model request was sent."""

    def iteration(  # noqa: B027, an optional hook
        self, state: "State", loop: str, iteration: int
    ) -> None:
        """A loop finished an iteration, e.g. to checkpoint."""

    @abstractmethod
    def finish(self, result: "GraphResult", state: "State") -> None:
        """The run ended."""


def _fingerprint(value: Any) -> Any:
    """An input, with the size and sha256 of the file it names, if it does,
    so the dataset a run used is known without copying it."""
    if not isinstance(value, str) or not Path(value).is_file():
        return value
    path = Path(value)
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def _inputs(inputs: dict[str, Any], exclude: Path) -> dict[str, Any]:
    recorded = {}
    for name, value in inputs.items():
        # A directory, e.g. a dataset's, is fingerprinted by its files, but
        # not by what's kept of experiments in it.
        if isinstance(value, str) and Path(value).is_dir():
            files = sorted(
                p
                for p in Path(value).rglob("*")
                if p.is_file() and not p.resolve().is_relative_to(exclude)
            )
            recorded[name] = {
                "path": value,
                "files": [_fingerprint(str(p)) for p in files],
            }
        else:
            recorded[name] = _fingerprint(value)
    return recorded


def _now() -> str:
    return datetime.now(UTC).isoformat()


class HostStore(RunStore):
    """
    Keeps an experiment in a directory on this machine:

        <root>/<experiment>/
          experiment.json     its name, and when it was created
          tree.json           every artifact's lineage, score and metadata
          tree.txt            the tree as text, tree.render()
          artifacts/<id>/     each artifact's files, and diff.patch from its parent
          metrics.jsonl       every evaluation, with its run and iteration
          memory.json         the memory, carried from run to run
          state.json          the current artifact, which the next run continues from
          runs/<run-id>/
            run.json          status, error, start and end, inputs, parent
            pipeline.txt      the pipeline as it ran, graph.describe()
            requests.jsonl    every model request, with its content
            traces.jsonl      the run's spans, with tracing.setup(store.spans())

    A run started to evaluate another experiment's artifact, e.g. a pipeline
    an optimizer proposed, names it as its parent. checkpoint_every saves
    the tree and memory every that many iterations of a loop, so a long run
    can be continued from near where it stopped.
    """

    def __init__(
        self,
        root: str | Path,
        experiment: str,
        parent: dict[str, str] | None = None,
        checkpoint_every: int | None = None,
    ):
        self.path = Path(root) / experiment
        self.experiment = experiment
        self.parent = parent
        self.checkpoint_every = checkpoint_every
        self.run_id = None
        self._run: dict[str, Any] = {}
        (self.path / "artifacts").mkdir(parents=True, exist_ok=True)
        (self.path / "runs").mkdir(exist_ok=True)
        info = self.path / "experiment.json"
        if not info.exists():
            info.write_text(
                json.dumps({"name": experiment, "created_at": _now()}, indent=2) + "\n"
            )

    @property
    def run_path(self) -> Path | None:
        return self.path / "runs" / self.run_id if self.run_id else None

    def runs(self) -> list[dict[str, Any]]:
        """Every run of the experiment, in the order they started."""
        runs = [
            json.loads((path / "run.json").read_text())
            for path in (self.path / "runs").iterdir()
            if (path / "run.json").exists()
        ]
        return sorted(runs, key=lambda run: run["started_at"])

    def start(self, graph: "Graph", inputs: dict[str, Any]) -> str:
        self.run_id = f"{datetime.now(UTC):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
        self.run_path.mkdir(parents=True)
        self._run = {
            "id": self.run_id,
            "experiment": self.experiment,
            "pipeline": graph.name,
            "status": "running",
            "started_at": _now(),
            "inputs": _inputs(inputs, self.path.parent.resolve()),
            "parent": self.parent,
        }
        self._write_run()
        (self.run_path / "pipeline.txt").write_text(graph.describe() + "\n")
        return self.run_id

    def artifact(self, artifact: Artifact, tree: Tree | None = None) -> None:
        directory = self.path / "artifacts" / artifact.id
        directory.mkdir(parents=True, exist_ok=True)
        if isinstance(artifact.content, Files):
            for name, text in artifact.content.files.items():
                file = directory / name
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(text)
        else:
            (directory / "content.json").write_text(
                json.dumps(artifact.content, default=str, indent=2)
            )
        # What changed from its parent, e.g. a program's edits.
        if tree is not None and artifact.parent_id is not None:
            (directory / "diff.patch").write_text(tree.diff(artifact.id))

    def metrics(
        self, state: "State", node: str, artifact_id: str, metrics: Metrics
    ) -> None:
        self._append(
            self.path / "metrics.jsonl",
            {
                "run": self.run_id,
                "iteration": current_iterations(),
                "branch": state.branch,
                "step": state.step,
                "node": node,
                "artifact_id": artifact_id,
                "score": metrics.score,
                "primary": metrics.primary,
                "values": metrics.values,
                "time": _now(),
            },
        )

    def request(self, record: RequestRecord) -> None:
        with (self.run_path / "requests.jsonl").open("a") as f:
            f.write(record.model_dump_json() + "\n")

    def iteration(self, state: "State", loop: str, iteration: int) -> None:
        if self.checkpoint_every and iteration % self.checkpoint_every == 0:
            self._save(state)

    def finish(self, result: "GraphResult", state: "State") -> None:
        self._save(state)
        self._run.update(
            status=result.status.value, error=result.error, ended_at=_now()
        )
        self._write_run()
        self.run_id = None

    def spans(self) -> SpanExporter:
        """An exporter writing each span to the traces of the run it's part
        of, for tracing.setup()."""
        return _RunSpans(self)

    def load(self) -> "State":
        """The experiment's state, as its last run ended or checkpointed, to
        continue it with another run."""
        from alphatrion.swarm.state import State

        if not (self.path / "tree.json").exists():
            return State()
        current = json.loads((self.path / "state.json").read_text())["current_id"]
        return State(
            memory=Memory.load(self.path / "memory.json"),
            tree=Tree.load(self.path / "tree.json"),
            current_id=current,
        )

    def _save(self, state: "State") -> None:
        state.tree.save(self.path / "tree.json")
        (self.path / "tree.txt").write_text(state.tree.render() + "\n")
        state.memory.save(self.path / "memory.json")
        # The artifact the next run continues from.
        (self.path / "state.json").write_text(
            json.dumps({"current_id": state.current_id}) + "\n"
        )

    def _append(self, path: Path, record: dict[str, Any]) -> None:
        with path.open("a") as f:
            f.write(json.dumps(record, default=str) + "\n")

    def _write_run(self) -> None:
        (self.run_path / "run.json").write_text(json.dumps(self._run, indent=2) + "\n")


class _RunSpans(SpanExporter):
    def __init__(self, store: HostStore):
        self.store = store

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        path = self.store.run_path
        if path is not None:
            with (path / "traces.jsonl").open("a") as f:
                for span in spans:
                    f.write(json.dumps(span_record(span), default=str) + "\n")
        return SpanExportResult.SUCCESS
