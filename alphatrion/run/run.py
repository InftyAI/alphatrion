import asyncio
import contextvars
import uuid

from alphatrion.metadata.sql_models import Status
from alphatrion.runtime.runtime import global_runtime

current_run_id = contextvars.ContextVar("current_run_id", default=None)


class Run:
    __slots__ = ("_id", "_task", "_runtime", "_trial_id")

    def __init__(self, trial_id: uuid.UUID):
        self._runtime = global_runtime()
        self._trial_id = trial_id

    @property
    def id(self) -> uuid.UUID:
        return self._id

    def _get_obj(self):
        return self._runtime._metadb.get_run(run_id=self._id)

    def start(self, call_func: callable) -> None:
        self._id = self._runtime._metadb.create_run(
            project_id=self._runtime._project_id,
            experiment_id=self._runtime.current_exp.id,
            trial_id=self._trial_id,
            status=Status.RUNNING,
        )

        # current_run_id context var is used in tracing workflow/task decorators.
        token = current_run_id.set(self.id)
        try:
            # The created task will also inherit the current context,
            # including the current_trial_id, current_run_id context var.
            self._task = asyncio.create_task(call_func())
        finally:
            current_run_id.reset(token)

    def done(self):
        # Callback will always be called even if the run is cancelled.
        # Make sure we don't update the status if it's already cancelled.
        if self.cancelled():
            return

        self._runtime._metadb.update_run(
            run_id=self._id,
            status=Status.COMPLETED,
        )

    def cancelled(self) -> bool:
        return self._task.cancelled()

    def cancel(self):
        self._task.cancel()
        self._runtime._metadb.update_run(
            run_id=self._id,
            status=Status.CANCELLED,
        )

    async def wait(self):
        await self._task

    def add_done_callback(self, callbacks: callable):
        self._task.add_done_callback(callbacks)
