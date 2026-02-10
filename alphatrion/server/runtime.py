# ruff: noqa: PLW0603
import os

from alphatrion import envs
from alphatrion.storage.sqlstore import SQLStore

__SERVER_RUNTIME__ = None


class ServerRuntime:
    _metadb = None

    def __init__(self, init_tables: bool = False):
        self._metadb = SQLStore(
            os.getenv(envs.METADATA_DB_URL), init_tables=init_tables
        )

    @property
    def metadb(self):
        return self._metadb


def init(init_tables: bool = False):
    """
    Initialize the Server runtime environment.
    """

    global __SERVER_RUNTIME__
    if __SERVER_RUNTIME__ is None:
        __SERVER_RUNTIME__ = ServerRuntime(init_tables=init_tables)


def server_runtime() -> ServerRuntime:
    if __SERVER_RUNTIME__ is None:
        raise RuntimeError("ServerRuntime is not initialized. Call init() first.")
    return __SERVER_RUNTIME__
