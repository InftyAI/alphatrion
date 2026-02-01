# ruff: noqa: PLW0603
import os
import uuid

from alphatrion import envs
from alphatrion.artifact.artifact import Artifact
from alphatrion.storage.sqlstore import SQLStore

__RUNTIME__ = None


def init(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
):
    """
    Initialize the AlphaTrion runtime environment.

    :param project_id: the project ID to initialize the environment.
                       For testing purpose, you can use a random UUID.
    :param artifact_insecure: whether to use insecure connection to the
        artifact registry
    """
    global __RUNTIME__
    __RUNTIME__ = Runtime(
        team_id=team_id,
        user_id=user_id,
    )


def global_runtime():
    if __RUNTIME__ is None:
        raise RuntimeError("Runtime is not initialized. Call alphatrion.init() first.")
    return __RUNTIME__


# Runtime contains all kinds of clients, e.g., metadb client, artifact client, etc.
# Stateful information will also be stored here, e.g., current running Project.
class Runtime:
    __slots__ = (
        "_user_id",
        "_team_id",
        "_metadb",
        "_artifact",
        "__current_proj",
        "_root_path",
    )

    def __init__(
        self,
        team_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        init_tables = os.getenv(envs.INIT_METADATA_TABLES, "false").lower() == "true"
        self._metadb = SQLStore(
            os.getenv(envs.METADATA_DB_URL), init_tables=init_tables
        )

        self._user_id = user_id
        self._team_id = team_id
        self._root_path = os.getenv(envs.ROOT_PATH, os.path.expanduser("~/.alphatrion"))

        artifact_insecure = os.getenv(envs.ARTIFACT_INSECURE, "false").lower() == "true"

        if self.artifact_storage_enabled():
            self._artifact = Artifact(team_id=self._team_id, insecure=artifact_insecure)

        if not os.path.exists(self._root_path):
            os.makedirs(self._root_path, exist_ok=True)

    def artifact_storage_enabled(self) -> bool:
        return os.getenv(envs.ENABLE_ARTIFACT_STORAGE, "true").lower() == "true"

    # current_proj is the current running Project.
    @property
    def current_proj(self):
        return self.__current_proj

    @current_proj.setter
    def current_proj(self, value) -> None:
        self.__current_proj = value

    @property
    def metadb(self) -> SQLStore:
        return self._metadb

    @property
    def user_id(self) -> uuid.UUID:
        return self._user_id

    @property
    def team_id(self) -> uuid.UUID:
        return self._team_id
