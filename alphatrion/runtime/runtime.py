# ruff: noqa: PLW0603
import os
import uuid

from alphatrion import consts
from alphatrion.artifact.artifact import Artifact
from alphatrion.metadata.sql import SQLStore

__RUNTIME__ = None


def init(
    project_id: uuid.UUID,
    artifact_insecure: bool = False,
    init_tables: bool = False,
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
        project_id=project_id,
        artifact_insecure=artifact_insecure,
        init_tables=init_tables,
    )


def global_runtime():
    if __RUNTIME__ is None:
        raise RuntimeError("Runtime is not initialized. Call alphatrion.init() first.")
    return __RUNTIME__


# Runtime contains all kinds of clients, e.g., metadb client, artifact client, etc.
# Stateful information will also be stored here, e.g., current running experiment ID.
class Runtime:
    __slots__ = ("_project_id", "_metadb", "_artifact", "__current_exp")

    def __init__(
        self,
        project_id: str,
        artifact_insecure: bool = False,
        init_tables: bool = False,
    ):
        self._project_id = project_id
        self._metadb = SQLStore(
            os.getenv(consts.METADATA_DB_URL), init_tables=init_tables
        )
        self._artifact = Artifact(
            project_id=self._project_id, insecure=artifact_insecure
        )

    # current_exp is the current running experiment.
    @property
    def current_exp(self):
        return self.__current_exp

    @current_exp.setter
    def current_exp(self, value):
        self.__current_exp = value
