import os

from alphatrion import consts
from alphatrion.database.sql import SQLDatabase


class Runtime:
    def __init__(self, project_id: str):
        self._project_id = project_id
        # TODO: initialize the metadata database based on the URL.
        self._metadb = SQLDatabase(os.getenv(consts.METADATA_DB_URL), init_tables=True)
