import uuid
from collections.abc import Awaitable, Callable
from typing import Any

CallableEntry = Callable[[], Awaitable[Any]]
PostRunHook = Callable[[uuid.UUID, Any], None]
