# ruff: noqa: PLW0603
import os
import uuid

from alphatrion import envs
from alphatrion.artifact.artifact import Artifact
from alphatrion.storage import runtime as storage_runtime
from alphatrion.storage.sqlstore import SQLStore

__RUNTIME__ = None


def init(
    user_id: uuid.UUID,
    team_id: uuid.UUID | None = None,
):
    """
    Initialize the AlphaTrion runtime environment.

    Args:
        user_id: The user ID for the current user. You can generate a UUID
                 using `uuid.uuid4()`.
        team_id: The team ID for the current user. If not provided, will look
                 for the first team
                 associated with the user in the database.
    """
    global __RUNTIME__
    __RUNTIME__ = Runtime(
        user_id=user_id,
        team_id=team_id,
    )


def global_runtime():
    if __RUNTIME__ is None:
        raise RuntimeError("Runtime is not initialized. Call alphatrion.init() first.")
    return __RUNTIME__


# Runtime contains all kinds of clients, e.g., metadb client, artifact client, etc.
# Stateful information will also be stored here.
class Runtime:
    __slots__ = (
        "_user_id",
        "_team_id",
        "_metadb",
        "_tracestore",
        "_artifact",
        "_root_path",
        "_current_experiment",
    )

    def __init__(
        self,
        user_id: uuid.UUID,
        team_id: uuid.UUID | None = None,
    ):
        storage_runtime.init()
        self._metadb = storage_runtime.storage_runtime().metadb
        self._tracestore = storage_runtime.storage_runtime().tracestore

        self._user_id = user_id
        self._team_id = team_id

        if team_id is None:
            # If team_id is not provided, look for the first team associated with
            # the user in the database.
            teams = self._metadb.list_user_teams(user_id)
            if len(teams) == 0:
                raise ValueError(
                    f"No team found for user_id {user_id}. Make sure the user is "
                    f"associated with at least one team in the database."
                )
            self._team_id = teams[0].uuid

        self._root_path = os.getenv(envs.ROOT_PATH, os.path.expanduser("~/.alphatrion"))

        artifact_insecure = os.getenv(envs.ARTIFACT_INSECURE, "false").lower() == "true"

        if self.artifact_storage_enabled():
            self._artifact = Artifact(team_id=self._team_id, insecure=artifact_insecure)

        if not os.path.exists(self._root_path):
            os.makedirs(self._root_path, exist_ok=True)

    def artifact_storage_enabled(self) -> bool:
        return os.getenv(envs.ENABLE_ARTIFACT_STORAGE, "true").lower() == "true"

    @property
    def metadb(self) -> SQLStore:
        return self._metadb

    @property
    def tracestore(self):
        return self._tracestore

    @property
    def user_id(self) -> uuid.UUID:
        return self._user_id

    @property
    def team_id(self) -> uuid.UUID:
        return self._team_id

    @property
    def root_path(self) -> str:
        return self._root_path

    @property
    def current_experiment(self):
        return self._current_experiment

    @current_experiment.setter
    def current_experiment(self, exp):
        self._current_experiment = exp
