import asyncio
import contextvars
import uuid

from alphatrion.runtime.runtime import global_runtime
from alphatrion.storage.sql_models import Status

current_run_id = contextvars.ContextVar("current_run_id", default=None)


class Run:
    __slots__ = ("_id", "_task", "_runtime", "_exp_id")

    def __init__(self, exp_id: uuid.UUID):
        self._runtime = global_runtime()
        self._exp_id = exp_id

    @property
    def id(self) -> uuid.UUID:
        return self._id

    def _get_obj(self):
        return self._runtime._metadb.get_run(run_id=self._id)

    def start(self, call_func: callable) -> None:
        self._id = self._runtime._metadb.create_run(
            team_id=self._runtime.team_id,
            user_id=self._runtime.user_id,
            project_id=self._runtime.current_proj.id,
            experiment_id=self._exp_id,
            status=Status.RUNNING,
        )

        # current_run_id context var is used in tracing workflow/task decorators.
        # exp.run() will be called sequentially, so it's safe to set the context var.
        token = current_run_id.set(self.id)
        try:
            # The created task will also inherit the current context,
            # including the current_exp_id, current_run_id context var.
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

    def cancel(self):
        # TODO: we should wait for the task to be actually cancelled
        # and catch the CancelledError exception in the task function.
        self._task.cancel()
        self._runtime._metadb.update_run(
            run_id=self._id,
            status=Status.CANCELLED,
        )

    def cancelled(self) -> bool:
        return self._task.cancelled()

    async def wait(self):
        await self._task

    def add_done_callback(self, callbacks: callable):
        self._task.add_done_callback(callbacks)
