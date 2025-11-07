import asyncio
import contextvars
import uuid

from alphatrion.runtime.runtime import global_runtime

current_run_id = contextvars.ContextVar("current_run_id", default=None)


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

    def register_task(self, task: asyncio.Task):
        self._task = task

    async def wait(self):
        await self._task
