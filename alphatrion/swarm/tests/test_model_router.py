from collections import Counter
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import openai
import pytest

from alphatrion.swarm import (
    GraphStatus,
    ModelRequest,
    ModelResponse,
    State,
    Text,
    build_graph,
)
from alphatrion.swarm.providers import ModelError, ModelRefusal
from alphatrion.swarm.providers.anthropic import AnthropicClient
from alphatrion.swarm.providers.openai import OpenAIClient


class FakeClient:
    """Answers with the model id, or fails for the models in failures."""

    def __init__(self, failures: dict[str, Exception] | None = None):
        self.failures = failures or {}
        self.requests: list[tuple[str, ModelRequest, int]] = []

    async def complete(self, model, request, max_tokens, params) -> ModelResponse:
        self.requests.append((model, request, max_tokens))
        if model in self.failures:
            raise self.failures[model]
        return ModelResponse(text=f"reply from {model}", model=model)


def ask(state) -> ModelRequest:
    return ModelRequest(messages=[{"role": "user", "content": "hello"}])


def router(**fields):
    return {
        "name": "ask",
        "type": "model_router",
        "params": {"request": "${nodes.prompt.output}"},
        "candidates": [
            {"model": "a", "provider": "fake"},
            {"model": "b", "provider": "fake"},
        ],
        **fields,
    }


PROMPT = {"name": "prompt", "type": "action", "fn": "prompt"}


def build(client, nodes, prompt=ask, **functions):
    # The router sends the ModelRequest prompt builds.
    return build_graph(
        {"nodes": [PROMPT, *nodes]},
        functions={"fake": client, "prompt": prompt, **functions},
    )


@pytest.mark.asyncio
async def test_fallback_on_errors_and_refusals():
    for failure in (ModelError("timeout"), ModelRefusal("declined")):
        client = FakeClient(failures={"a": failure})
        result = await build(client, [router(policy="fallback")]).run()

        assert result.status == GraphStatus.COMPLETED
        # The router outputs the ModelResponse, which carries its request's
        # number.
        assert result.output == ModelResponse(
            text="reply from b", model="b", metadata={"request": 2}
        )
        entry = result.state.memory.history(node="ask")[0]
        assert entry.data["details"] == [str(failure)]
        assert [model for model, _, _ in client.requests] == ["a", "b"]
        # Every attempt is in the state's requests, in order.
        requests = list(result.state.requests)
        assert [(r.number, r.model, r.error) for r in requests] == [
            (1, "a", str(failure)),
            (2, "b", None),
        ]
        assert requests[1].response.text == "reply from b"
        assert requests[0].node == "ask"


@pytest.mark.asyncio
async def test_every_candidate_failing():
    client = FakeClient(failures={"a": ModelError("down"), "b": ModelError("down")})

    # Without handling the error choice, the node fails.
    result = await build(client, [router()]).run()
    assert result.status == GraphStatus.FAILED
    assert "every candidate failed" in result.error

    # With it, the node chooses failed, without an output, and the branch
    # can still reference the request before it.
    seen = []

    def recover(state, request: ModelRequest):
        seen.append(request.messages[0]["content"])

    recover_node = {
        "name": "recover",
        "type": "action",
        "fn": "recover",
        "params": {"request": "${nodes.prompt.output}"},
    }
    graph = build(
        client, [router(branches={"failed": [recover_node]})], recover=recover
    )
    result = await graph.run()
    assert result.status == GraphStatus.COMPLETED
    assert seen == ["hello"]


@pytest.mark.asyncio
async def test_weighted_policy():
    client = FakeClient()
    node = router(
        seed=0,
        candidates=[
            {"model": "a", "provider": "fake", "weight": 9},
            {"model": "b", "provider": "fake", "weight": 1},
        ],
    )
    loop = {"name": "loop", "type": "loop", "max_iters": 500, "nodes": [PROMPT, node]}
    graph = build_graph({"nodes": [loop]}, functions={"fake": client, "prompt": ask})
    await graph.run()

    picks = Counter(model for model, _, _ in client.requests)
    assert picks["a"] + picks["b"] == 500
    assert 400 < picks["a"] < 490


@pytest.mark.asyncio
async def test_router_sends_the_request_it_references():
    client = FakeClient()

    # The task is an input of the run, which prompt turns into the request.
    def prompt(state: State, task: str) -> ModelRequest:
        return ModelRequest(
            system="be brief", messages=[{"role": "user", "content": task}]
        )

    graph = build_graph(
        {
            "inputs": ["task"],
            "nodes": [
                {**PROMPT, "params": {"task": "${inputs.task}"}},
                router(max_tokens=128),
            ],
        },
        functions={"fake": client, "prompt": prompt},
    )
    await graph.run(inputs={"task": "improve train.py"})
    _, request, max_tokens = client.requests[0]
    assert request.system == "be brief"
    assert request.messages == [{"role": "user", "content": "improve train.py"}]
    assert max_tokens == 128


def test_router_formats_are_checked():
    def not_a_request(state) -> Text:
        return Text(content="hi")

    with pytest.raises(
        ValueError,
        match=r"Node ask param request takes ModelRequest, but \$\{nodes.prompt.output\} is Text",
    ):
        build(FakeClient(), [router()], prompt=not_a_request)


def test_provider_inference_and_lazy_clients():
    # Building needs no API keys: clients are created on first use.
    graph = build(
        None,
        [
            router(
                candidates=[
                    {"model": "claude-opus-5-5"},
                    {"model": "llama-4", "base_url": "http://localhost:8000/v1"},
                ]
            )
        ],
    )
    candidates = graph.nodes["ask"].candidates
    assert [c.provider_name for c in candidates] == ["anthropic", "openai"]


def test_the_request_is_a_param():
    # Checked like any node's params, from run(self, state, request).
    with pytest.raises(ValueError, match="Node ask takes 'request', which the node"):
        build(FakeClient(), [router(params={})])
    with pytest.raises(ValueError, match="params it doesn't take: tokens"):
        build(
            FakeClient(),
            [router(params={"request": "${nodes.prompt.output}", "tokens": 9})],
        )
    with pytest.raises(
        ValueError, match="Node ask param request: expected ModelRequest"
    ):
        build(FakeClient(), [router(params={"request": "hi"})])


def test_invalid_router():
    with pytest.raises(ValueError):
        build(FakeClient(), [router(candidates=[])])
    with pytest.raises(ValueError):
        build(FakeClient(), [router(policy="random")])
    with pytest.raises(ValueError, match="has no choice 'fail'"):
        build(FakeClient(), [router(exit={"fail": "end"})])


REQUEST = ModelRequest(system="be brief", messages=[{"role": "user", "content": "hi"}])


class FakeStream:
    """Stands in for client.messages.stream(...), recording its arguments."""

    def __init__(self, message):
        self.message = message
        self.kwargs = None

    def __call__(self, **kwargs):
        self.kwargs = kwargs
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get_final_message(self):
        return self.message


@pytest.mark.asyncio
async def test_anthropic_client():
    client = AnthropicClient(api_key="test")
    stream = FakeStream(
        SimpleNamespace(
            stop_reason="end_turn",
            content=[
                SimpleNamespace(type="thinking", thinking=""),
                SimpleNamespace(type="text", text="an idea"),
            ],
            usage=SimpleNamespace(input_tokens=10, output_tokens=3),
        )
    )
    client._client.messages.stream = stream

    response = await client.complete("claude-opus-5-5", REQUEST, 64, {})
    assert response == ModelResponse(
        text="an idea",
        model="claude-opus-5-5",
        metadata={"provider": "anthropic"},
        input_tokens=10,
        output_tokens=3,
    )
    assert stream.kwargs == {
        "model": "claude-opus-5-5",
        "max_tokens": 64,
        "messages": [{"role": "user", "content": "hi"}],
        "system": "be brief",
    }

    for stop_reason, error in (("refusal", ModelRefusal), ("max_tokens", ModelError)):
        stream.message = SimpleNamespace(
            stop_reason=stop_reason, content=[], usage=None
        )
        with pytest.raises(error):
            await client.complete("claude-opus-5-5", REQUEST, 64, {})


@pytest.mark.asyncio
async def test_openai_client():
    client = OpenAIClient(api_key="test")
    create = AsyncMock(
        return_value=SimpleNamespace(
            choices=[
                SimpleNamespace(
                    finish_reason="stop", message=SimpleNamespace(content="an idea")
                )
            ],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=3),
        )
    )
    client._client.chat.completions.create = create

    response = await client.complete("llama-4", REQUEST, 64, {})
    assert response.text == "an idea"
    assert (response.input_tokens, response.output_tokens) == (10, 3)
    # The system prompt becomes the first message.
    assert create.call_args.kwargs["messages"][0] == {
        "role": "system",
        "content": "be brief",
    }

    create.side_effect = openai.APIConnectionError(
        request=httpx.Request("POST", "http://localhost")
    )
    with pytest.raises(ModelError):
        await client.complete("llama-4", REQUEST, 64, {})


@pytest.mark.asyncio
async def test_a_mistake_fails_the_router_even_if_failed_is_handled():
    class Broken:
        async def complete(self, model, request, max_tokens, options):
            raise TypeError("no credentials")

    # failed is for models failing, so a mistake isn't retried silently.
    graph = build(Broken(), [router(exit={"failed": "end"})])
    result = await graph.run()
    assert result.status == GraphStatus.FAILED
    assert "TypeError: no credentials" in result.error
    # The attempt is recorded all the same.
    (record,) = result.state.requests
    assert record.error == "TypeError: no credentials"


def test_bedrock_ids_use_bedrock():
    graph = build(
        None,
        [
            router(
                candidates=[
                    {"model": "us.anthropic.claude-opus-5-5"},
                    {"model": "anthropic.claude-sonnet-5-5", "region": "eu-west-1"},
                    {"model": "claude-opus-5-5"},
                ]
            )
        ],
    )
    node = graph.nodes["ask"]
    assert [c.provider_name for c in node.candidates] == [
        "bedrock",
        "bedrock",
        "anthropic",
    ]
    # Built from the AWS environment, without an Anthropic API key.
    from alphatrion.swarm.providers.anthropic import BedrockClient

    assert isinstance(node._client(0), BedrockClient)
    assert node._client(1)._client.aws_region == "eu-west-1"


def test_claude_needs_an_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    graph = build(None, [router(candidates=[{"model": "claude-opus-5-5"}])])
    with pytest.raises(RuntimeError, match="claude-opus-5-5 needs an API key"):
        graph.nodes["ask"]._client(0)
