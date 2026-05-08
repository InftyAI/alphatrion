import asyncio
import uuid
from datetime import UTC, datetime

from alphatrion.runtime.contextvars import current_run_id
from alphatrion.runtime.runtime import global_runtime
from alphatrion.storage.sql_models import Status
from alphatrion.types import CallableEntry, PostRunHookFn


class Run:
    __slots__ = ("_id", "_task", "_runtime", "_exp_id", "_result", "_post_run_hooks")

    def __init__(
        self, exp_id: uuid.UUID, post_run_hooks: list[PostRunHookFn] | None = None
    ):
        self._runtime = global_runtime()
        self._exp_id = exp_id
        self._result = None
        self._post_run_hooks = post_run_hooks or []

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
            org_id=self._runtime.org_id,
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
        # Also since it's cancelled, no need to execute the post-run hooks.
        if self.cancelled():
            return

        run = self._runtime._metadb.get_run(run_id=self.id)
        duration = (
            datetime.now(UTC) - run.created_at.replace(tzinfo=UTC)
        ).total_seconds()

        # Try to get the result, but handle failures gracefully
        try:
            self._result = self._task.result()
            status = Status.COMPLETED
        except Exception as e:
            # Task failed - store the exception
            self._result = e
            status = Status.FAILED
            import traceback

            print(f"Run {self._id} failed with exception: {e}")
            traceback.print_exc()

        # Update run with status and duration
        self._runtime.metadb.update_run(
            run_id=self._id,
            status=status,
            duration=duration,
        )

        # Execute post-run hooks only if successful
        if status == Status.COMPLETED:
            for hook in self._post_run_hooks:
                try:
                    hook(self.id, self._result)
                except Exception as e:
                    # Log error but don't fail the run
                    import traceback

                    print(f"Warning: Post-run hook {hook.__name__} failed: {e}")
                    traceback.print_exc()

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
