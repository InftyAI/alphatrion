import uuid

from alphatrion.runtime.runtime import global_runtime


class Run:
    def __init__(self, trial_id: uuid.UUID):
        self._runtime = global_runtime()
        self._trial_id = trial_id

    @property
    def id(self) -> uuid.UUID:
        return self._id

    def _start(self):
        self._id = self._runtime._metadb.create_run(
            project_id=self._runtime._project_id, trial_id=self._trial_id
        )
