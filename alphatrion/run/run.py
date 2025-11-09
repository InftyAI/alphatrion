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

    def _start(self, call_func: callable) -> asyncio.Task | None:
        self._id = self._runtime._metadb.create_run(
            project_id=self._runtime._project_id, trial_id=self._trial_id
        )

        # current_run_id context var is used in tracing workflow/task decorators.
        token = current_run_id.set(self.id)
        try:
            # The created task will also inherit the current context,
            # including the current_trial_id, current_run_id context var.
            self._task = asyncio.create_task(call_func())
        finally:
            current_run_id.reset(token)

        return self._task

    async def wait(self):
        await self._task
