import pytest

from alphatrion.swarm import ModelRequest, ModelResponse, State, build_graph, tracing
from alphatrion.swarm.providers.base import ModelError

REQUEST = ModelRequest(system="be brief", messages=[{"role": "user", "content": "hi"}])


class FakeClient:
    """Answers as the model, failing for those in fail."""

    def __init__(self, fail=()):
        self.fail = set(fail)

    async def complete(self, model, request, max_tokens, options):
        if model in self.fail:
            raise ModelError(f"{model} is down")
        return ModelResponse(
            text=f"from {model}", model=model, input_tokens=5, output_tokens=7
        )


def prompt(state) -> ModelRequest:
    return REQUEST


def pipeline(policy="fallback", iterations=1, weights=(1, 1)):
    return {
        "nodes": [
            {
                "name": "repeat",
                "type": "loop",
                "max_iters": iterations,
                "nodes": [
                    {"name": "prompt", "type": "action", "fn": "prompt"},
                    {
                        "name": "ask",
                        "type": "model_router",
                        "params": {"request": "${nodes.prompt.output}"},
                        "policy": policy,
                        "seed": 0,
                        "candidates": [
                            {"model": "a", "provider": "fake", "weight": weights[0]},
                            {"model": "b", "provider": "fake", "weight": weights[1]},
                        ],
                    },
                ],
            }
        ]
    }


@pytest.fixture
def host(tmp_path):
    exporter = tracing.HostExporter(tmp_path / "traces.jsonl")
    tracing.setup(exporter)
    yield exporter
    tracing.setup()


@pytest.mark.asyncio
async def test_model_requests_nest_under_their_node_and_run(host):
    graph = build_graph(
        pipeline(), functions={"fake": FakeClient(fail={"a"}), "prompt": prompt}
    )
    result = await graph.run()
    assert result.status.value == "completed", result.error

    spans = {s["name"]: s for s in host.records()}
    run, node, failed, ok = (
        spans["run graph"],
        spans["node ask"],
        spans["model a"],
        spans["model b"],
    )
    # The model requests nest under the node that sent them, in the run.
    assert failed["parent_id"] == ok["parent_id"] == node["span_id"]
    assert {s["trace_id"] for s in spans.values()} == {run["trace_id"]}
    # Every attempt is a request span, with OpenInference's LLM attributes.
    assert failed["status"] == "ERROR"
    assert failed["attributes"]["swarm.request.number"] == 1
    attributes = ok["attributes"]
    assert attributes["openinference.span.kind"] == "LLM"
    assert attributes["llm.model_name"] == "b"
    assert ModelRequest.model_validate_json(attributes["input.value"]) == REQUEST
    assert attributes["output.value"] == "from b"
    assert attributes["llm.token_count.prompt"] == 5
    assert attributes["swarm.request.number"] == 2
    assert node["attributes"]["swarm.node.type"] == "model_router"


@pytest.mark.asyncio
async def test_spans_to_a_database(tmp_path):
    database = tracing.DatabaseExporter(tmp_path / "traces.db")
    tracing.setup(database)
    try:
        graph = build_graph(
            pipeline(policy="weighted", iterations=40, weights=(3, 1)),
            functions={"fake": FakeClient(), "prompt": prompt},
        )
        state = State()
        await graph.run(state=state)
        # Requests by model, from the database, match the run's own count.
        rows = dict(
            database.query(
                "SELECT model, COUNT(*) FROM spans WHERE model IS NOT NULL "
                "GROUP BY model"
            )
        )
    finally:
        # Shutting down the tracer closes the database.
        tracing.setup()
    assert rows == dict(state.requests.counts())
    assert rows["a"] > rows["b"] and rows["a"] + rows["b"] == 40


@pytest.mark.asyncio
async def test_failures_are_traced(host):
    def broken(state):
        raise ValueError("boom")

    result = await build_graph(
        {"nodes": [{"name": "broken", "type": "action", "fn": broken}]}
    ).run()
    assert result.status.value == "failed"
    spans = {s["name"]: s for s in host.records()}
    assert spans["node broken"]["status"] == "ERROR"
    assert spans["node broken"]["attributes"]["swarm.choice"] == "error"
    assert spans["run graph"]["attributes"]["swarm.status"] == "failed"


@pytest.mark.asyncio
async def test_the_run_keeps_its_requests_in_order():
    graph = build_graph(
        pipeline(), functions={"fake": FakeClient(fail={"a"}), "prompt": prompt}
    )
    result = await graph.run()
    records = list(result.state.requests)
    assert [(r.number, r.model, r.error) for r in records] == [
        (1, "a", "a is down"),
        (2, "b", None),
    ]
    # The response carries its request's number.
    assert result.output.metadata["request"] == 2
