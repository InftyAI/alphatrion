import enum
from collections.abc import Iterator
from typing import Any

from alphatrion.swarm.context import current_runtime
from alphatrion.swarm.memory import Memory, MemoryEntry
from alphatrion.swarm.state import State
from alphatrion.swarm.tree import Artifact, ScoreMode, Tree


class Capability(enum.StrEnum):
    """What a node may change in the state, beyond reading it, which every
    node can. A node type declares the most its nodes can have, and each
    node can narrow them."""

    # Add artifacts to the tree and move the current one.
    COMMIT = "commit"
    # Write the memory store.
    REMEMBER = "remember"
    # Score artifacts. Only evaluators have it, and they score what their
    # fn measures, so no function ever scores directly.
    SCORE = "score"


class CapabilityError(PermissionError):
    pass


def _require(state: State, granted: frozenset[Capability], cap: Capability) -> None:
    if cap not in granted:
        raise CapabilityError(
            f"Node {state.node} has no {cap.value} capability"
            + (f", only {', '.join(sorted(granted))}" if granted else "")
        )


class TreeView:
    """The tree, read-only."""

    def __init__(self, tree: Tree):
        self._tree = tree

    @property
    def root(self) -> Artifact | None:
        return self._tree.root

    def get(self, artifact_id: str) -> Artifact:
        return self._tree.get(artifact_id)

    def parent(self, artifact_id: str) -> Artifact | None:
        return self._tree.parent(artifact_id)

    def children(self, artifact_id: str) -> list[Artifact]:
        return self._tree.children(artifact_id)

    def leaves(self) -> list[Artifact]:
        return self._tree.leaves()

    def lineage(self, artifact_id: str) -> list[Artifact]:
        return self._tree.lineage(artifact_id)

    def depth(self, artifact_id: str) -> int:
        return self._tree.depth(artifact_id)

    def best(self, mode: ScoreMode = ScoreMode.MAX) -> Artifact | None:
        return self._tree.best(mode)

    def __len__(self) -> int:
        return len(self._tree)

    def __contains__(self, artifact_id: str) -> bool:
        return artifact_id in self._tree

    def __iter__(self) -> Iterator[Artifact]:
        return iter(self._tree)


class MemoryView:
    """The memory: the history is read-only, since only the graph records
    it, and the store is writable with the remember capability."""

    def __init__(self, state: State, granted: frozenset[Capability]):
        self._state = state
        self._memory: Memory = state.memory
        self._granted = granted

    def history(self, *args: Any, **kwargs: Any) -> list[MemoryEntry]:
        return self._memory.history(*args, **kwargs)

    def get(self, key: str, default: Any = None) -> Any:
        return self._memory.get(key, default)

    def set(self, key: str, value: Any) -> None:
        _require(self._state, self._granted, Capability.REMEMBER)
        self._memory.set(key, value)

    def __contains__(self, key: str) -> bool:
        return key in self._memory

    def __len__(self) -> int:
        return len(self._memory)

    def __iter__(self) -> Iterator[MemoryEntry]:
        return iter(self._memory)


class StateView:
    """
    The state as a node function sees it, limited to the node's
    capabilities: reading is always allowed, commit() and checkout() need
    commit, and memory.set() needs remember. The tree is read-only, so
    artifacts are only added through commit(), and scored only by
    evaluators.
    """

    def __init__(self, state: State, granted: frozenset[Capability]):
        self._state = state
        self.granted = granted
        self.tree = TreeView(state.tree)
        self.memory = MemoryView(state, granted)

    @property
    def runtime(self) -> Any:
        """The runtime the node runs in, e.g. to exec a command in it."""
        runtime = current_runtime()
        if runtime is None:
            raise RuntimeError(
                f"Node {self._state.node} has no runtime: give it one with "
                "runtime: in the pipeline"
            )
        return runtime

    @property
    def current(self) -> Artifact | None:
        return self._state.current

    @property
    def current_id(self) -> str | None:
        return self._state.current_id

    @property
    def branch(self) -> str | None:
        return self._state.branch

    @property
    def step(self) -> int:
        return self._state.step

    @property
    def node(self) -> str | None:
        return self._state.node

    def commit(self, content: Any, metadata: dict[str, Any] | None = None) -> Artifact:
        _require(self._state, self.granted, Capability.COMMIT)
        return self._state.commit(content, metadata=metadata)

    def checkout(self, artifact_id: str) -> Artifact:
        _require(self._state, self.granted, Capability.COMMIT)
        return self._state.checkout(artifact_id)
