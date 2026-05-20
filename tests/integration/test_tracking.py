"""Integration tests for LLM token tracking and cost calculation.

Tests validate:
- Token tracking (input, output, total, cache tokens)
- Cost calculation and enrichment
- Storage in ClickHouse
- Prometheus metrics export
"""

import uuid

import pytest
from openai import OpenAI

from alphatrion import experiment, tracing
from alphatrion.storage import runtime


@pytest.fixture(scope="module")
def test_org_id() -> uuid.UUID:
    """Organization ID for testing."""
    return uuid.uuid4()


@pytest.fixture(scope="module")
def test_team_id(test_org_id: uuid.UUID, test_user_id: uuid.UUID) -> uuid.UUID:
    """Create test team."""
    runtime.init()
    metadb = runtime.storage_runtime().metadb

    user = metadb.get_user(user_id=test_user_id)
    if not user:
        metadb.create_user(
            org_id=test_org_id,
            name="Token Test User",
            email=f"test-{test_user_id}@example.com",
            uuid=test_user_id,
        )

    team_id = metadb.create_team(
        org_id=test_org_id,
        name="Token Test Team",
        description="Team for token tracking tests",
    )

    from alphatrion.storage.sql_models import MemberRole

    metadb.add_user_to_team(
        user_id=test_user_id,
        team_id=team_id,
        role=MemberRole.SUPER_ADMIN,
    )

    return team_id


@pytest.fixture(scope="module")
def test_user_id() -> uuid.UUID:
    """User ID for testing."""
    return uuid.uuid4()


@pytest.fixture(scope="module")
def openai_client():
    """OpenAI client pointing to local Ollama."""
    import os

    ollama_port = os.getenv("OLLAMA_PORT", "21434")
    return OpenAI(
        base_url=f"http://localhost:{ollama_port}/v1",
        api_key="",
    )


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_token_tracking_and_storage(
    test_org_id: uuid.UUID,
    test_team_id: uuid.UUID,
    test_user_id: uuid.UUID,
    openai_client: OpenAI,
):
    """Test that tokens are tracked, stored in ClickHouse, and costs are calculated."""
    import alphatrion as alpha

    # Initialize with test IDs
    alpha.init(
        org_id=str(test_org_id),
        team_id=str(test_team_id),
        user_id=str(test_user_id),
    )

    experiment_id = None

    @tracing.task()
    def make_llm_call(prompt: str):
        """Make LLM call with token tracking."""
        completion = openai_client.chat.completions.create(
            model="smollm:135m",
            messages=[{"role": "user", "content": prompt}],
        )
        return completion.choices[0].message.content

    @tracing.workflow()
    async def token_workflow():
        """Workflow with multiple LLM calls."""
        result1 = make_llm_call("What is 2+2?")
        result2 = make_llm_call("What is the capital of France?")
        return result1, result2

    # Run experiment
    async with experiment.CraftExperiment.start(name="token_tracking_test") as exp:
        experiment_id = exp.id
        task = exp.run(token_workflow)
        await task.wait()

    # Verify tokens in ClickHouse
    runtime.init()
    tracestore = runtime.storage_runtime().tracestore

    assert tracestore is not None, (
        "Tracestore is not initialized, cannot verify token tracking"
    )

    # Query spans with token data (use tracestore database name)
    database = tracestore.database

    query = f"""
    SELECT
        SpanId as span_id,
        SpanName as span_name,
        SpanAttributes['gen_ai.usage.input_tokens'] as input_tokens,
        SpanAttributes['gen_ai.usage.output_tokens'] as output_tokens,
        SpanAttributes['gen_ai.usage.cache_read_input_tokens'] as cache_read_tokens,
        SpanAttributes['gen_ai.usage.cache_creation_input_tokens'] as cache_creation_tokens,
        SpanAttributes['alphatrion.cost.input_tokens'] as input_cost,
        SpanAttributes['alphatrion.cost.output_tokens'] as output_cost,
        SpanAttributes['alphatrion.cost.cache_read_input_tokens'] as cache_read_cost,
        SpanAttributes['alphatrion.cost.cache_creation_input_tokens'] as cache_creation_cost,
        SpanAttributes['gen_ai.response.model'] as model,
        TeamId as team_id,
        ExperimentId as experiment_id
    FROM {database}.otel_spans
    WHERE ExperimentId = '{experiment_id}'
        AND mapContains(SpanAttributes, 'gen_ai.usage.input_tokens')
    ORDER BY Timestamp DESC
    """

    spans = tracestore.client.query(query).result_rows
    # Validate 2 LLM calls were tracked
    assert len(spans) == 2, (
        f"Expected at least 2 spans with token data, got {len(spans)}"
    )

    # Validate each span
    for span in spans:
        (
            span_id,
            span_name,
            input_tokens,
            output_tokens,
            cache_read_tokens,
            cache_creation_tokens,
            input_cost,
            output_cost,
            cache_read_cost,
            cache_creation_cost,
            model,
            team_id,
            exp_id,
        ) = span

        # Validate token fields exist and are positive
        assert input_tokens, f"Span {span_id}: input_tokens is missing"
        assert int(input_tokens) > 0, f"Span {span_id}: input_tokens must be > 0"

        assert output_tokens, f"Span {span_id}: output_tokens is missing"
        assert int(output_tokens) > 0, f"Span {span_id}: output_tokens must be > 0"

        # Calculate total tokens from components
        inp = int(input_tokens)
        out = int(output_tokens)
        cache_read = int(cache_read_tokens) if cache_read_tokens else 0
        cache_creation = int(cache_creation_tokens) if cache_creation_tokens else 0

        assert inp > 0 and out > 0, (
            f"Span {span_id}: input and output tokens must be > 0"
        )
        # Validate cache tokens are non-negative
        assert cache_read >= 0, f"Span {span_id}: cache_read_tokens must be >= 0"
        assert cache_creation >= 0, (
            f"Span {span_id}: cache_creation_tokens must be >= 0"
        )

        # Validate cost fields exist and are non-negative
        assert input_cost, f"Span {span_id}: input_cost is missing"
        inp_c = float(input_cost)
        assert inp_c >= 0, f"Span {span_id}: input_cost must be >= 0"

        assert output_cost, f"Span {span_id}: output_cost is missing"
        out_c = float(output_cost)
        assert out_c >= 0, f"Span {span_id}: output_cost must be >= 0"

        # Validate cache cost fields are non-negative (may be empty)
        cache_read_c = float(cache_read_cost) if cache_read_cost else 0.0
        cache_creation_c = float(cache_creation_cost) if cache_creation_cost else 0.0
        assert cache_read_c >= 0, f"Span {span_id}: cache_read_cost must be >= 0"
        assert cache_creation_c >= 0, (
            f"Span {span_id}: cache_creation_cost must be >= 0"
        )

        # Validate metadata
        assert model == "smollm:135m", f"Span {span_id}: unexpected model {model}"
        assert team_id == str(test_team_id), f"Span {span_id}: wrong team_id"
        assert exp_id == str(experiment_id), f"Span {span_id}: wrong experiment_id"


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_prometheus_metrics_export(
    test_org_id: uuid.UUID,
    test_team_id: uuid.UUID,
    test_user_id: uuid.UUID,
    openai_client: OpenAI,
):
    """Test that metrics are exported to Prometheus push gateway."""
    import os

    import alphatrion as alpha

    # Skip if Prometheus is not enabled
    enable_prometheus = os.getenv("ALPHATRION_ENABLE_PROMETHEUS_EXPORTER", "true")
    assert enable_prometheus.lower() == "true", (
        "Prometheus exporter not enabled, cannot test metrics export"
    )

    alpha.init(
        org_id=str(test_org_id),
        team_id=str(test_team_id),
        user_id=str(test_user_id),
    )

    @tracing.task()
    def simple_llm_call():
        completion = openai_client.chat.completions.create(
            model="smollm:135m",
            messages=[{"role": "user", "content": "Say hello"}],
        )
        return completion.choices[0].message.content

    @tracing.workflow()
    async def prometheus_workflow():
        simple_llm_call()

    async with experiment.CraftExperiment.start(name="prometheus_metrics_test") as exp:
        task = exp.run(prometheus_workflow)
        await task.wait()

    # Force flush span processors to ensure metrics are pushed
    from opentelemetry import trace

    tracer_provider = trace.get_tracer_provider()
    if hasattr(tracer_provider, "_active_span_processor"):
        tracer_provider._active_span_processor.force_flush()

    # Verify spans were created first
    runtime.init()
    tracestore = runtime.storage_runtime().tracestore
    if tracestore is None:
        pytest.fail("ClickHouse not available - cannot verify metrics")

    database = tracestore.database
    span_check_query = f"""
    SELECT count(*) as span_count
    FROM {database}.otel_spans
    WHERE mapContains(SpanAttributes, 'gen_ai.usage.input_tokens')
    """
    span_count = tracestore.client.query(span_check_query).result_rows[0][0]

    if span_count == 0:
        pytest.fail(
            "No LLM spans found in ClickHouse. "
            "Either Ollama failed or spans weren't exported. "
            "Check that Ollama is running with smollm:135m model."
        )

    # Query push gateway metrics
    import httpx

    pushgateway_url = os.getenv(
        "ALPHATRION_PROMETHEUS_PUSHGATEWAY_URL", "localhost:29091"
    )

    try:
        response = httpx.get(f"http://{pushgateway_url}/metrics", timeout=5.0)
        metrics = response.text

        # Validate token metrics exist (with token_type label)
        assert "llm_tokens_total" in metrics, "llm_tokens_total metric not found"
        assert 'token_type="total"' in metrics, "token_type=total label not found"
        assert 'token_type="input"' in metrics, "token_type=input label not found"
        assert 'token_type="output"' in metrics, "token_type=output label not found"

        # Validate cost metrics exist (with token_type label)
        assert "llm_cost_total" in metrics, "llm_cost_total metric not found"
        # Cost metrics should also have token_type labels

        # Validate request metrics exist
        assert "llm_requests_total" in metrics, "llm_requests_total metric not found"
        assert "llm_request_duration_seconds" in metrics, (
            "llm_request_duration_seconds not found"
        )

        # Validate our test IDs appear in labels
        assert str(test_team_id) in metrics, "test_team_id not in metrics"
        assert "smollm:135m" in metrics, "model name not in metrics"

    except httpx.ConnectError:
        pytest.skip("Prometheus push gateway not available")


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_aggregated_usage_via_graphql(
    test_org_id: uuid.UUID,
    test_team_id: uuid.UUID,
    test_user_id: uuid.UUID,
    openai_client: OpenAI,
):
    """Test that aggregated token usage is queryable via GraphQL."""
    import alphatrion as alpha

    alpha.init(
        org_id=str(test_org_id),
        team_id=str(test_team_id),
        user_id=str(test_user_id),
    )

    @tracing.task()
    def tracked_call():
        return openai_client.chat.completions.create(
            model="smollm:135m",
            messages=[{"role": "user", "content": "Count to 3"}],
        )

    @tracing.workflow()
    async def usage_workflow():
        tracked_call()
        tracked_call()

    experiment_id = None
    async with experiment.CraftExperiment.start(name="usage_aggregation_test") as exp:
        experiment_id = exp.id
        task = exp.run(usage_workflow)
        await task.wait()

    # Query aggregated usage via GraphQL resolvers
    from unittest.mock import Mock

    from alphatrion.server.graphql.context import GraphQLContext
    from alphatrion.server.graphql.resolvers import GraphQLResolvers

    mock_request = Mock()
    context = GraphQLContext(
        org_id=str(test_org_id),
        user_id=str(test_user_id),
        request=mock_request,
    )

    info = Mock()
    info.context = context

    # Get experiment usage
    usage = GraphQLResolvers.aggregate_experiment_usage(
        info=info,
        experiment_id=str(experiment_id),
    )

    # Validate aggregated usage
    assert usage["total_tokens"] > 0, "total_tokens should be > 0"
    assert usage["input_tokens"] > 0, "input_tokens should be > 0"
    assert usage["output_tokens"] > 0, "output_tokens should be > 0"
    assert usage["total_cost"] >= 0, "total_cost should be >= 0"

    # Validate token math
    assert usage["total_tokens"] == usage["input_tokens"] + usage["output_tokens"], (
        "total_tokens should equal sum of input and output tokens"
    )
