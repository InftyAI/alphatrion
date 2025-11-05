import asyncio
from collections.abc import Callable


# Inspired by golang context package
class Context:
    def __init__(self, cancel_func: Callable | None = None, timeout=None):
        """A context for managing cancellation and timeouts.
        :param cancel_func: A function to call when the context is cancelled.
        :param timeout: Timeout in seconds. If None, no timeout is set.
        """
        self._cancel_event = asyncio.Event()
        self._cancel_func = cancel_func
        self._timeout = timeout

    def start(self):
        # If timeout is None, it means no timeout is set.
        # If timeout is negative, it means already timed out.
        if self._timeout is not None:
            asyncio.create_task(self._auto_cancel(self._timeout))

    async def _auto_cancel(self, timeout):
        await asyncio.sleep(timeout)
        self.cancel()

    def cancel(self):
        if self.cancelled():
            return
        if self._cancel_func:
            self._cancel_func()
        self._cancel_event.set()

    def cancelled(self):
        return self._cancel_event.is_set()

    async def wait(self):
        await self._cancel_event.wait()
