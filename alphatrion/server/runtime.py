# ruff: noqa: PLW0603
import os

from alphatrion import envs
from alphatrion.storage.sqlstore import SQLStore

__SERVER_RUNTIME__ = None


class ServerRuntime:
    _metadb = None
    _inited = False

    def __init__(self):
        if self._inited:
            return

        init_tables = os.getenv(envs.INIT_METADATA_TABLES, "false").lower() == "true"
        self._metadb = SQLStore(
            os.getenv(envs.METADATA_DB_URL), init_tables=init_tables
        )
        self._inited = True

    @property
    def metadb(self):
        return self._metadb


def init():
    """
    Initialize the Server runtime environment.
    """

    global __SERVER_RUNTIME__
    if __SERVER_RUNTIME__ is None:
        __SERVER_RUNTIME__ = ServerRuntime()


def server_runtime() -> ServerRuntime:
    if __SERVER_RUNTIME__ is None:
        raise RuntimeError("ServerRuntime is not initialized. Call init() first.")
    return __SERVER_RUNTIME__
