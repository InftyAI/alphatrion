import os

from alphatrion import consts
from alphatrion.metadata.sql import SQLStore


class Runtime:
    def __init__(self, project_id: str):
        self._project_id = project_id
        self._metadb = SQLStore(os.getenv(consts.METADATA_DB_URL), init_tables=True)
