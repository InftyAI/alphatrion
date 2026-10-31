import os
import random
import time
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from openinference.semconv.trace import SpanAttributes
from opentelemetry import trace
from pydantic import BaseModel, ConfigDict, Field, PrivateAttr

from alphatrion.swarm import tracing
from alphatrion.swarm.context import current_iterations, current_store
from alphatrion.swarm.formats import (
    ModelRequest,
    ModelResponse,
)
from alphatrion.swarm.nodes.base import Node, NodeResult
from alphatrion.swarm.providers.base import ModelClient, ModelError
from alphatrion.swarm.state import State

if TYPE_CHECKING:
    from alphatrion.swarm.pipeline import Builder


class Candidate(BaseModel):
    """A model the router can send the request to."""

    model_config = ConfigDict(extra="forbid")

    model: str = Field(description="The model id, e.g. claude-opus-5-5.")
    provider: str | None = Field(
        default=None,
        description="openai, anthropic, bedrock, or a custom client resolved like "
        "an action fn. Inferred from the model id if None: bedrock for Bedrock's "
        "ids, e.g. us.anthropic.claude-opus-5-5, anthropic for claude-*, and "
        "openai otherwise.",
    )
    weight: float = Field(default=1.0, gt=0, description="Used by the weighted policy.")
    base_url: str | None = Field(
        default=None,
        description="The API endpoint, e.g. of a vLLM or OpenRouter server.",
    )
    region: str | None = Field(
        default=None,
        description="The AWS region for Bedrock, AWS_REGION's by default.",
    )
    api_key_env: str | None = Field(
        default=None,
        description="The environment variable holding the API key, the "
        "provider's default if None.",
    )
    options: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra request settings for this model's API, passed as is, "
        "e.g. {output_config: {effort: high}}.",
    )

    @property
    def provider_name(self) -> str:
        if self.provider is not None:
            return self.provider
        # Bedrock's ids, e.g. us.anthropic.claude-opus-5-5 or
        # anthropic.claude-sonnet-5-5.
        if self.model.startswith("anthropic.") or ".anthropic." in self.model:
            return "bedrock"
        return "anthropic" if self.model.startswith("claude") else "openai"


class ModelRouterNode(Node):
    """
    Sends the ModelRequest its request param references, e.g.
    `params: {request: ${nodes.prompt.output}}`, to one of several candidate
    models, e.g. to propose an improvement, and outputs the ModelResponse. The
    weighted policy tries the candidates in a random order drawn by weight,
    and the fallback policy in their listed order. A failed attempt, e.g. a
    timeout, a rate limit or a refusal, moves on to the next candidate.

    It chooses "ok", with the failed attempts as details. When every
    candidate fails, it chooses "failed", without an output, if the node
    handles that choice, and fails otherwise. Anything but a model failing,
    e.g. a missing API key, fails the node at once, on its error choice.
    """

    choices: ClassVar[frozenset[str] | None] = frozenset({"ok", "failed"})

    type: Literal["model_router"] = "model_router"
    candidates: list[Candidate] = Field(min_length=1)
    policy: Literal["weighted", "fallback"] = "weighted"
    max_tokens: int = Field(default=16000, ge=1)
    seed: int | None = Field(
        default=None, description="Seeds the weighted policy, for reproducible runs."
    )

    _custom: dict[int, Any] = PrivateAttr(default_factory=dict)
    _clients: dict[int, ModelClient] = PrivateAttr(default_factory=dict)
    _rng: random.Random = PrivateAttr()

    def _prepare(self, builder: "Builder") -> None:
        self._rng = random.Random(self.seed)
        for i, candidate in enumerate(self.candidates):
            if candidate.provider_name not in ("openai", "anthropic", "bedrock"):
                self._custom[i] = builder.resolve(candidate.provider_name)

    def _client(self, i: int) -> ModelClient:
        # Built-in clients are created on first use, so building a pipeline
        # doesn't require API keys.
        if i not in self._clients:
            candidate = self.candidates[i]
            if i in self._custom:
                custom = self._custom[i]
                client = custom if hasattr(custom, "complete") else custom()
            else:
                api_key = (
                    os.environ.get(candidate.api_key_env)
                    if candidate.api_key_env
                    else None
                )
                if candidate.provider_name == "bedrock":
                    from alphatrion.swarm.providers.anthropic import BedrockClient

                    client = BedrockClient(
                        region=candidate.region, base_url=candidate.base_url
                    )
                elif candidate.provider_name == "anthropic":
                    if api_key is None and not (
                        os.environ.get("ANTHROPIC_API_KEY")
                        or os.environ.get("ANTHROPIC_AUTH_TOKEN")
                    ):
                        raise RuntimeError(
                            f"{candidate.model} needs an API key: set "
                            "ANTHROPIC_API_KEY, or the candidate's api_key_env"
                        )
                    from alphatrion.swarm.providers.anthropic import AnthropicClient

                    client = AnthropicClient(
                        base_url=candidate.base_url, api_key=api_key
                    )
                else:
                    from alphatrion.swarm.providers.openai import OpenAIClient

                    client = OpenAIClient(base_url=candidate.base_url, api_key=api_key)
            self._clients[i] = client
        return self._clients[i]

    def _order(self) -> list[int]:
        indices = list(range(len(self.candidates)))
        if self.policy == "fallback":
            return indices
        # Weighted sampling without replacement: the first candidate is drawn
        # by weight, and so is each fallback among the remaining ones.
        return sorted(
            indices,
            key=lambda i: self._rng.random() ** (1 / self.candidates[i].weight),
            reverse=True,
        )

    def _log(
        self,
        state: State,
        candidate: Candidate,
        request: ModelRequest,
        start: float,
        **result: Any,
    ):
        """Record a request in the state's requests, every attempt included,
        and in the run's store, if it has one."""
        record = state.requests.add(
            node=state.node or self.name,
            branch=state.branch,
            iteration=current_iterations(),
            model=candidate.model,
            request=request,
            duration=time.monotonic() - start,
            artifact_id=state.current_id,
            **result,
        )
        store = current_store()
        if store is not None:
            store.request(record)
        return record

    @property
    def _handles_error(self) -> bool:
        if "failed" in self.branches or isinstance(self.exit, str):
            return True
        return isinstance(self.exit, dict) and bool(
            {"failed", "default"} & set(self.exit)
        )

    def output_type(self) -> Any:
        return ModelResponse

    def outputs_on(self, choice: str | None) -> bool:
        return choice == "ok"

    async def run(self, state: State, request: ModelRequest) -> NodeResult:
        errors = []
        for i in self._order():
            candidate = self.candidates[i]
            # Each attempt is a model request span, OpenInference's LLM kind.
            with tracing.tracer().start_as_current_span(
                f"model {candidate.model}"
            ) as span:
                span.set_attribute(tracing.KIND, tracing.LLM)
                span.set_attribute(SpanAttributes.LLM_MODEL_NAME, candidate.model)
                span.set_attribute(
                    SpanAttributes.INPUT_VALUE, request.model_dump_json()
                )
                span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "application/json")
                span.set_attribute("swarm.node", state.node or self.name)
                if state.current_id is not None:
                    span.set_attribute("swarm.artifact_id", state.current_id)
                start = time.monotonic()
                try:
                    response = await self._client(i).complete(
                        candidate.model, request, self.max_tokens, candidate.options
                    )
                except Exception as e:
                    error = (
                        str(e)
                        if isinstance(e, ModelError)
                        else f"{type(e).__name__}: {e}"
                    )
                    record = self._log(state, candidate, request, start, error=error)
                    span.set_attribute("swarm.request.number", record.number)
                    span.set_status(trace.Status(trace.StatusCode.ERROR, error))
                    # A model that failed, e.g. timed out or refused, is
                    # skipped for the next; anything else, e.g. a missing
                    # API key, is a mistake, failing the node.
                    if not isinstance(e, ModelError):
                        raise
                    errors.append(error)
                    continue
                record = self._log(state, candidate, request, start, response=response)
                span.set_attribute("swarm.request.number", record.number)
                span.set_attribute(SpanAttributes.OUTPUT_VALUE, response.text)
                for attribute, tokens in (
                    (SpanAttributes.LLM_TOKEN_COUNT_PROMPT, response.input_tokens),
                    (SpanAttributes.LLM_TOKEN_COUNT_COMPLETION, response.output_tokens),
                ):
                    if tokens is not None:
                        span.set_attribute(attribute, tokens)
            # The response carries its request's number, so what it leads to,
            # e.g. an artifact, can record which request and model it came from.
            response.metadata["request"] = record.number
            return NodeResult(choice="ok", output=response, details=errors)

        if self._handles_error:
            return NodeResult(choice="failed", details=errors)
        raise RuntimeError(
            f"Model router {self.name}: every candidate failed: {'; '.join(errors)}"
        )
