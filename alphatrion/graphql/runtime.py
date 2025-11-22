# ruff: noqa: PLW0603
import os

from alphatrion import consts
from alphatrion.metadata.sql import SQLStore

__GRAPHQL_RUNTIME__ = None


class GraphQLRuntime:
    _metadb = None

    def __init__(self, init_tables: bool = False):
        self._metadb = SQLStore(
            os.getenv(consts.METADATA_DB_URL), init_tables=init_tables
        )

    @property
    def metadb(self):
        return self._metadb


def init(init_tables: bool = False):
    """
    Initialize the GraphQL runtime environment.
    """

    global __GRAPHQL_RUNTIME__
    if __GRAPHQL_RUNTIME__ is None:
        __GRAPHQL_RUNTIME__ = GraphQLRuntime(init_tables=init_tables)


def graphql_runtime() -> GraphQLRuntime:
    if __GRAPHQL_RUNTIME__ is None:
        raise RuntimeError("GraphQLRuntime is not initialized. Call init() first.")
    return __GRAPHQL_RUNTIME__
