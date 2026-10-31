from typing import Any

import openai

from alphatrion.swarm.formats import ModelRequest, ModelResponse
from alphatrion.swarm.providers.base import ModelError, ModelRefusal


class OpenAIClient:
    """
    Calls models through the OpenAI Chat Completions API, or any server
    compatible with it, e.g. vLLM, OpenRouter or DeepInfra, with base_url.
    """

    provider = "openai"

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self._client = openai.AsyncOpenAI(base_url=base_url, api_key=api_key)

    async def complete(
        self,
        model: str,
        request: ModelRequest,
        max_tokens: int,
        params: dict[str, Any],
    ) -> ModelResponse:
        messages = list(request.messages)
        if request.system:
            messages = [{"role": "system", "content": request.system}, *messages]
        try:
            response = await self._client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                **params,
            )
        except openai.APIError as e:
            raise ModelError(f"{model}: {e}") from e

        if not response.choices:
            raise ModelError(f"{model}: the response has no choices")
        choice = response.choices[0]
        if choice.finish_reason == "content_filter":
            raise ModelRefusal(f"{model}: the response was filtered")
        if choice.finish_reason == "length":
            raise ModelError(f"{model}: the response was cut off at max_tokens")
        usage = response.usage
        return ModelResponse(
            text=choice.message.content or "",
            model=model,
            metadata={"provider": self.provider},
            input_tokens=usage.prompt_tokens if usage else None,
            output_tokens=usage.completion_tokens if usage else None,
        )
