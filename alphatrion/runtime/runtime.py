import os

from alphatrion import consts
from alphatrion.metadata.sql import SQLMetadata


class Runtime:
    def __init__(self, project_id: str):
        self._project_id = project_id
        # TODO: initialize the metadata database based on the URL.
        self._metadb = SQLMetadata(os.getenv(consts.METADATA_DB_URL), init_tables=True)
