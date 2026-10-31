import difflib
import enum
import json
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from alphatrion.swarm.formats import Format


class Artifact(BaseModel):
    """One version of an artifact, e.g. a prompt, a program or an agent config.
    Each artifact derives from its parent, so the artifacts form a tree that
    records how the artifact evolved."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    parent_id: str | None = None
    content: Any = None
    # Frozen, so only an evaluator node can score an artifact, through the
    # tree: the code being improved can propose artifacts but not judge them.
    score: float | None = Field(
        default=None,
        frozen=True,
        description="The evaluation score, None if not evaluated.",
    )
    created_by: str | None = Field(
        default=None, description="The name of the node that created the artifact."
    )
    run: str | None = Field(default=None, description="The run that made it.")
    iteration: dict[str, int] = Field(
        default_factory=dict,
        description="Where in the run it was made: each loop's iteration.",
    )
    branch: str | None = Field(default=None, description="Its parallel branch.")
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ScoreMode(enum.Enum):
    MAX = "max"
    MIN = "min"


class Tree:
    """
    A tree recording the evolution of an artifact. The root is the initial
    artifact, and each child is a variant derived from its parent. Branching
    lets a graph explore several variants from the same parent, and
    backtrack to an earlier artifact when a branch doesn't improve.
    """

    def __init__(self):
        self._artifacts: dict[str, Artifact] = {}
        self._children: dict[str, list[str]] = {}
        self._root_id: str | None = None

    @property
    def root(self) -> Artifact | None:
        return self._artifacts.get(self._root_id) if self._root_id else None

    def add(
        self,
        content: Any,
        parent_id: str | None = None,
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
        **where: Any,
    ) -> Artifact:
        """Add an unscored artifact. Only an evaluator node scores it. where
        is the run, iteration and branch it was made in."""
        return self._insert(
            Artifact(
                parent_id=parent_id,
                content=content,
                created_by=created_by,
                metadata=metadata or {},
                **where,
            )
        )

    def _insert(self, artifact: Artifact) -> Artifact:
        if artifact.id in self._artifacts:
            raise ValueError(f"Artifact {artifact.id} already exists")
        if artifact.parent_id is None:
            if self._root_id is not None:
                raise ValueError("The tree already has a root, parent_id is required")
            self._root_id = artifact.id
        elif artifact.parent_id not in self._artifacts:
            raise KeyError(f"Parent artifact {artifact.parent_id} not found")
        else:
            self._children[artifact.parent_id].append(artifact.id)

        self._artifacts[artifact.id] = artifact
        self._children[artifact.id] = []
        return artifact

    def get(self, artifact_id: str) -> Artifact:
        try:
            return self._artifacts[artifact_id]
        except KeyError:
            raise KeyError(f"Artifact {artifact_id} not found") from None

    def _set_score(self, artifact_id: str, score: float) -> Artifact:
        """Score an artifact. Private to the evaluator node, which is the only
        place scores come from, since the evaluation is never improved."""
        artifact = self.get(artifact_id)
        # score is frozen against assignment, so it's written directly.
        artifact.__dict__["score"] = score
        return artifact

    def parent(self, artifact_id: str) -> Artifact | None:
        parent_id = self.get(artifact_id).parent_id
        return self._artifacts[parent_id] if parent_id else None

    def children(self, artifact_id: str) -> list[Artifact]:
        self.get(artifact_id)
        return [self._artifacts[i] for i in self._children[artifact_id]]

    def leaves(self) -> list[Artifact]:
        return [a for a in self._artifacts.values() if not self._children[a.id]]

    def lineage(self, artifact_id: str) -> list[Artifact]:
        """Return the path from the root to the artifact, both included."""
        path = []
        current: Artifact | None = self.get(artifact_id)
        while current is not None:
            path.append(current)
            current = self.parent(current.id)
        return path[::-1]

    def depth(self, artifact_id: str) -> int:
        return len(self.lineage(artifact_id)) - 1

    def best(self, mode: ScoreMode = ScoreMode.MAX) -> Artifact | None:
        """Return the artifact with the best score, None if none is scored.
        On a tie, the earliest artifact wins."""
        scored = [a for a in self._artifacts.values() if a.score is not None]
        if not scored:
            return None
        if mode == ScoreMode.MAX:
            return max(scored, key=lambda a: a.score)
        return min(scored, key=lambda a: a.score)

    def diff(self, artifact_id: str) -> str:
        """What changed from the artifact's parent, as a unified diff of its
        files, e.g. a program's edits. The root's diff adds everything."""
        artifact = self.get(artifact_id)
        parent = self.parent(artifact_id)
        before = _files(parent.content) if parent is not None else {}
        after = _files(artifact.content)
        lines: list[str] = []
        for name in sorted(before.keys() | after.keys()):
            lines += difflib.unified_diff(
                before.get(name, "").splitlines(keepends=True),
                after.get(name, "").splitlines(keepends=True),
                fromfile=f"a/{name}",
                tofile=f"b/{name}",
            )
        return "".join(lines)

    def render(self, mode: ScoreMode = ScoreMode.MAX) -> str:
        """The tree as text: each artifact under its parent, with its score,
        or that it's unscored, its description, and how many lines it added
        and removed from its parent. The best one is marked with a star."""
        if self.root is None:
            return ""
        best = self.best(mode)
        lines: list[str] = []

        def line(artifact: Artifact) -> str:
            score = "unscored" if artifact.score is None else f"{artifact.score:.4f}"
            text = f"{artifact.id[:8]}  {score}  {artifact.metadata.get('description', '')}"
            if best is not None and artifact.id == best.id:
                text += " ★"
            if artifact.parent_id is not None:
                diff = self.diff(artifact.id).splitlines()
                added = sum(
                    1 for d in diff if d.startswith("+") and not d.startswith("+++")
                )
                removed = sum(
                    1 for d in diff if d.startswith("-") and not d.startswith("---")
                )
                text += f"  +{added} -{removed}"
            return text

        def walk(artifact: Artifact, prefix: str) -> None:
            children = self.children(artifact.id)
            for i, child in enumerate(children):
                last = i == len(children) - 1
                lines.append(f"{prefix}{'└── ' if last else '├── '}{line(child)}")
                walk(child, prefix + ("    " if last else "│   "))

        lines.append(line(self.root))
        walk(self.root, "")
        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._artifacts)

    def __contains__(self, artifact_id: str) -> bool:
        return artifact_id in self._artifacts

    def __iter__(self) -> Iterator[Artifact]:
        # Artifacts are kept in insertion order, so parents come before children.
        return iter(self._artifacts.values())

    def to_dict(self) -> dict[str, Any]:
        artifacts = []
        for a in self._artifacts.values():
            record = a.model_dump(mode="json", fallback=str)
            # Its content's format, e.g. Files, to load it back as one.
            if isinstance(a.content, Format):
                record["format"] = type(a.content).__name__
            artifacts.append(record)
        return {"artifacts": artifacts}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Tree":
        tree = cls()
        formats = _formats()
        for record in data.get("artifacts", []):
            fields = dict(record)
            fmt = formats.get(fields.pop("format", None))
            artifact = Artifact.model_validate(fields)
            if fmt is not None:
                artifact.content = fmt.model_validate(artifact.content)
            tree._insert(artifact)
        return tree

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "Tree":
        return cls.from_dict(json.loads(Path(path).read_text()))


def _files(content: Any) -> dict[str, str]:
    """An artifact's content as files: its files, or itself as one."""
    files = getattr(content, "files", None)
    if isinstance(files, dict):
        return files
    return {
        "content": content
        if isinstance(content, str)
        else json.dumps(content, default=str, indent=2)
    }


def _formats() -> dict[str, type[Format]]:
    """Every format by name, custom ones included, as they subclass Format."""
    found: dict[str, type[Format]] = {}
    pending = [Format]
    while pending:
        cls = pending.pop()
        found[cls.__name__] = cls
        pending.extend(cls.__subclasses__())
    return found
