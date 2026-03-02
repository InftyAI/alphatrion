import asyncio
import uuid
from datetime import UTC, datetime

from alphatrion.runtime.contextvars import current_run_id
from alphatrion.runtime.runtime import global_runtime
from alphatrion.storage.sql_models import Status
from alphatrion.types import CallableEntry


class Run:
    __slots__ = ("_id", "_task", "_runtime", "_exp_id", "_result")

    def __init__(self, exp_id: uuid.UUID):
        self._runtime = global_runtime()
        self._exp_id = exp_id
        self._result = None

    @property
    def id(self) -> uuid.UUID:
        return self._id

    @property
    def result(self) -> any:
        return self._result

    def _get_obj(self):
        return self._runtime.metadb.get_run(run_id=self._id)

    def start(self, call_func: CallableEntry) -> None:
        self._id = self._runtime.metadb.create_run(
            team_id=self._runtime.team_id,
            user_id=self._runtime.user_id,
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

        run = self._runtime._metadb.get_run(run_id=self.id)
        duration = (
            datetime.now(UTC) - run.created_at.replace(tzinfo=UTC)
        ).total_seconds()

        self._runtime.metadb.update_run(
            run_id=self._id, status=Status.COMPLETED, duration=duration
        )
        self._result = self._task.result()

    def cancel(self):
        # TODO: we should wait for the task to be actually cancelled
        # and catch the CancelledError exception in the task function.
        self._task.cancel()

        run = self._runtime._metadb.get_run(run_id=self.id)
        duration = (
            datetime.now(UTC) - run.created_at.replace(tzinfo=UTC)
        ).total_seconds()

        self._runtime.metadb.update_run(
            run_id=self._id, status=Status.CANCELLED, duration=duration
        )

    def cancelled(self) -> bool:
        return self._task.cancelled()

    async def wait(self):
        await self._task

    def add_done_callback(self, callbacks: callable):
        self._task.add_done_callback(callbacks)
