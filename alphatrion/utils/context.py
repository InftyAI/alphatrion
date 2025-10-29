import asyncio
from collections.abc import Callable


# Inspired by golang context package
class Context:
    def __init__(self, cancel_func: Callable | None = None, timeout=None):
        self._cancel_event = asyncio.Event()
        self._cancel_func = cancel_func
        self._timeout = timeout

    async def start(self):
        if self._timeout:
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

    async def wait_cancelled(self):
        await self._cancel_event.wait()
