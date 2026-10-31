from typing import Any

from alphatrion.swarm.formats import ModelRequest, ModelResponse
from alphatrion.swarm.providers.base import ModelError, ModelRefusal

try:
    import anthropic
except ImportError:  # pragma: no cover, depends on the install
    anthropic = None


class AnthropicClient:
    """
    Calls Claude models through the Anthropic Messages API. Requests are
    streamed, so long outputs, e.g. with thinking, don't hit HTTP timeouts.
    """

    provider = "anthropic"

    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        if anthropic is None:
            raise ImportError(
                "Claude models require the anthropic package, "
                "install it with `pip install alphatrion[anthropic]`"
            )
        # The SDK resolves credentials from the environment when api_key is
        # None, and retries rate limits and server errors itself.
        self._client = anthropic.AsyncAnthropic(base_url=base_url, api_key=api_key)

    async def complete(
        self,
        model: str,
        request: ModelRequest,
        max_tokens: int,
        params: dict[str, Any],
    ) -> ModelResponse:
        kwargs = dict(params)
        if request.system:
            kwargs["system"] = request.system
        try:
            async with self._client.messages.stream(
                model=model,
                max_tokens=max_tokens,
                messages=request.messages,
                **kwargs,
            ) as stream:
                response = await stream.get_final_message()
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as e:
            raise ModelError(f"{model}: {e}") from e

        if response.stop_reason == "refusal":
            raise ModelRefusal(f"{model}: the model declined the request")
        if response.stop_reason == "max_tokens":
            raise ModelError(f"{model}: the response was cut off at max_tokens")
        text = "".join(block.text for block in response.content if block.type == "text")
        return ModelResponse(
            text=text,
            model=model,
            metadata={"provider": self.provider},
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )


class BedrockClient(AnthropicClient):
    """
    Calls Claude models through AWS Bedrock, e.g. us.anthropic.claude-opus-5-5,
    with the AWS credentials of the environment, e.g. a profile or SSO, as
    Claude Code with CLAUDE_CODE_USE_BEDROCK does, and the region of
    AWS_REGION unless given. No Anthropic API key is needed.
    """

    provider = "bedrock"

    def __init__(self, region: str | None = None, base_url: str | None = None):
        if anthropic is None:
            raise ImportError(
                "Claude models on Bedrock require the anthropic package, "
                "install it with `pip install alphatrion[anthropic]`"
            )
        self._client = anthropic.AsyncAnthropicBedrock(
            aws_region=region, base_url=base_url
        )
