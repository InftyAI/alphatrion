# ruff: noqa: PLW0603
import os

from alphatrion import envs
from alphatrion.storage.sqlstore import SQLStore

__STORAGE_RUNTIME__ = None


class StorageRuntime:
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
    Initialize the Storage runtime environment.
    """

    global __STORAGE_RUNTIME__
    if __STORAGE_RUNTIME__ is None:
        __STORAGE_RUNTIME__ = StorageRuntime()


def storage_runtime() -> StorageRuntime:
    if __STORAGE_RUNTIME__ is None:
        raise RuntimeError("StorageRuntime is not initialized. Call init() first.")
    return __STORAGE_RUNTIME__
