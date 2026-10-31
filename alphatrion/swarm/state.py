from typing import Any

from alphatrion.swarm.context import current_iterations, current_store
from alphatrion.swarm.memory import Memory
from alphatrion.swarm.requests import Requests
from alphatrion.swarm.tree import Artifact, Tree


class State:
    """
    The state passed to every node of a graph run. It bundles:

    - memory: the history and the key-value store shared by the nodes.
    - tree: the tree of artifacts, plus a pointer to the current artifact,
      which nodes move with commit() and checkout(), like a git HEAD.
    - requests: every model request sent, in order, with its content.
    """

    def __init__(
        self,
        memory: Memory | None = None,
        tree: Tree | None = None,
        current_id: str | None = None,
        requests: Requests | None = None,
    ):
        self.memory = memory if memory is not None else Memory()
        self.requests = requests if requests is not None else Requests()
        self.tree = tree if tree is not None else Tree()
        if current_id is not None:
            self.tree.get(current_id)
        self.current_id = current_id
        # The name of the parallel branch running with this state, if any.
        self.branch: str | None = None
        # Both are maintained by the graph while running.
        self.step = 0
        self.node: str | None = None

    @property
    def current(self) -> Artifact | None:
        return self.tree.get(self.current_id) if self.current_id else None

    def commit(
        self,
        content: Any,
        metadata: dict[str, Any] | None = None,
    ) -> Artifact:
        """Add a new artifact derived from the current one and make it current.
        It is unscored until an evaluator node scores it."""
        store = current_store()
        artifact = self.tree.add(
            content,
            parent_id=self.current_id,
            created_by=self.node,
            metadata=metadata,
            run=store.run_id if store is not None else None,
            iteration=current_iterations(),
            branch=self.branch,
        )
        self.current_id = artifact.id
        if store is not None:
            store.artifact(artifact, self.tree)
        return artifact

    def checkout(self, artifact_id: str) -> Artifact:
        """Make an existing artifact current, e.g. to backtrack to a better one,
        so the next commit branches from it."""
        artifact = self.tree.get(artifact_id)
        self.current_id = artifact.id
        return artifact

    def fork(self, branch: str) -> "State":
        """Create the state of a parallel branch. It shares the memory, the
        tree and the requests, but has its own current artifact and step, so
        branches can evolve the artifact independently."""
        state = State(
            memory=self.memory,
            requests=self.requests,
            tree=self.tree,
            current_id=self.current_id,
        )
        state.branch = f"{self.branch}/{branch}" if self.branch else branch
        return state
