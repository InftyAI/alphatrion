from typing import Any, Protocol

from alphatrion.swarm.formats import ModelRequest, ModelResponse


class ModelError(Exception):
    """A failed model call, e.g. a timeout or a rate limit. The router tries
    the next candidate."""


class ModelRefusal(ModelError):
    """The model declined to answer. The router treats it like an error."""


class ModelClient(Protocol):
    async def complete(
        self,
        model: str,
        request: ModelRequest,
        max_tokens: int,
        params: dict[str, Any],
    ) -> ModelResponse: ...
