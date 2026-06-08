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


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_tool_decorator_tracking(
    test_org_id: uuid.UUID,
    test_team_id: uuid.UUID,
    test_user_id: uuid.UUID,
    openai_client: OpenAI,
):
    """Test that @tool decorator creates spans with correct semantic kind in ClickHouse."""
    import alphatrion as alpha

    alpha.init(
        org_id=str(test_org_id),
        team_id=str(test_team_id),
        user_id=str(test_user_id),
    )

    experiment_id = None

    @tracing.tool()
    def search_database(query: str) -> str:
        """Simulate a tool that searches a database."""
        return f"Results for: {query}"

    @tracing.tool()
    def calculate(x: int, y: int) -> int:
        """Simulate a calculation tool."""
        return x + y

    @tracing.workflow()
    async def tool_workflow():
        """Workflow that uses tools."""
        result1 = search_database("test query")
        result2 = calculate(5, 3)
        return result1, result2

    async with experiment.CraftExperiment.start(name="tool_tracking_test") as exp:
        experiment_id = exp.id
        task = exp.run(tool_workflow)
        await task.wait()

    # Query ClickHouse for tool spans
    runtime.init()
    tracestore = runtime.storage_runtime().tracestore
    assert tracestore is not None, "Tracestore not initialized"

    database = tracestore.database
    query = f"""
    SELECT
        SpanId,
        SpanName,
        SemanticKind,
        TeamId,
        ExperimentId,
        SpanAttributes['traceloop.span.kind'] as traceloop_kind
    FROM {database}.otel_spans
    WHERE ExperimentId = '{experiment_id}'
        AND SemanticKind = 'tool'
    ORDER BY Timestamp
    """

    spans = tracestore.client.query(query).result_rows
    assert len(spans) == 2, f"Expected 2 tool spans, got {len(spans)}"

    tool_names = {span[1] for span in spans}
    assert any("search_database" in name for name in tool_names), (
        f"search_database not found in {tool_names}"
    )
    assert any("calculate" in name for name in tool_names), (
        f"calculate not found in {tool_names}"
    )

    for span in spans:
        span_id, span_name, semantic_kind, team_id, exp_id, traceloop_kind = span

        assert semantic_kind == "tool", f"Span {span_id}: wrong semantic kind"
        assert traceloop_kind == "tool", f"Span {span_id}: wrong traceloop kind"
        assert team_id == str(test_team_id), f"Span {span_id}: wrong team_id"
        assert exp_id == str(experiment_id), f"Span {span_id}: wrong experiment_id"


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_agent_decorator_tracking(
    test_org_id: uuid.UUID,
    test_team_id: uuid.UUID,
    test_user_id: uuid.UUID,
    openai_client: OpenAI,
):
    """Test that @agent decorator creates spans with correct semantic kind in ClickHouse."""
    import alphatrion as alpha

    alpha.init(
        org_id=str(test_org_id),
        team_id=str(test_team_id),
        user_id=str(test_user_id),
    )

    experiment_id = None

    @tracing.agent()
    def research_agent(topic: str) -> str:
        """Simulate an agent that does research."""
        completion = openai_client.chat.completions.create(
            model="smollm:135m",
            messages=[{"role": "user", "content": f"Research: {topic}"}],
        )
        return completion.choices[0].message.content

    @tracing.agent()
    def planning_agent(goal: str) -> str:
        """Simulate an agent that creates plans."""
        return f"Plan for: {goal}"

    @tracing.workflow()
    async def agent_workflow():
        """Workflow that uses agents."""
        research = research_agent("AI trends")
        plan = planning_agent("launch product")
        return research, plan

    async with experiment.CraftExperiment.start(name="agent_tracking_test") as exp:
        experiment_id = exp.id
        task = exp.run(agent_workflow)
        await task.wait()

    # Query ClickHouse for agent spans
    runtime.init()
    tracestore = runtime.storage_runtime().tracestore
    assert tracestore is not None, "Tracestore not initialized"

    database = tracestore.database
    query = f"""
    SELECT
        SpanId,
        SpanName,
        SemanticKind,
        TeamId,
        ExperimentId,
        SpanAttributes['traceloop.span.kind'] as traceloop_kind
    FROM {database}.otel_spans
    WHERE ExperimentId = '{experiment_id}'
        AND SemanticKind = 'agent'
    ORDER BY Timestamp
    """

    spans = tracestore.client.query(query).result_rows
    assert len(spans) == 2, f"Expected 2 agent spans, got {len(spans)}"

    agent_names = {span[1] for span in spans}
    assert any("research_agent" in name for name in agent_names), (
        f"research_agent not found in {agent_names}"
    )
    assert any("planning_agent" in name for name in agent_names), (
        f"planning_agent not found in {agent_names}"
    )

    for span in spans:
        span_id, span_name, semantic_kind, team_id, exp_id, traceloop_kind = span

        assert semantic_kind == "agent", f"Span {span_id}: wrong semantic kind"
        assert traceloop_kind == "agent", f"Span {span_id}: wrong traceloop kind"
        assert team_id == str(test_team_id), f"Span {span_id}: wrong team_id"
        assert exp_id == str(experiment_id), f"Span {span_id}: wrong experiment_id"


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_agent_with_nested_tools(
    test_org_id: uuid.UUID,
    test_team_id: uuid.UUID,
    test_user_id: uuid.UUID,
    openai_client: OpenAI,
):
    """Test agent calling tools - verify span hierarchy and semantic kinds."""
    import alphatrion as alpha

    alpha.init(
        org_id=str(test_org_id),
        team_id=str(test_team_id),
        user_id=str(test_user_id),
    )

    experiment_id = None

    @tracing.tool()
    def fetch_data(source: str) -> str:
        """Tool that fetches data."""
        return f"Data from {source}"

    @tracing.tool()
    def process_data(data: str) -> str:
        """Tool that processes data."""
        return f"Processed: {data}"

    @tracing.agent()
    def data_agent(query: str) -> str:
        """Agent that uses tools."""
        raw = fetch_data("database")
        processed = process_data(raw)
        return processed

    @tracing.workflow()
    async def nested_workflow():
        """Workflow with agent using tools."""
        return data_agent("get user data")

    async with experiment.CraftExperiment.start(name="nested_tracking_test") as exp:
        experiment_id = exp.id
        task = exp.run(nested_workflow)
        await task.wait()

    # Query all spans and verify hierarchy
    runtime.init()
    tracestore = runtime.storage_runtime().tracestore
    assert tracestore is not None, "Tracestore not initialized"

    database = tracestore.database
    query = f"""
    SELECT
        SpanName,
        SemanticKind,
        COUNT(*) as count
    FROM {database}.otel_spans
    WHERE ExperimentId = '{experiment_id}'
    GROUP BY SpanName, SemanticKind
    ORDER BY SemanticKind, SpanName
    """

    results = tracestore.client.query(query).result_rows

    semantic_kinds = {row[1] for row in results}
    assert "agent" in semantic_kinds, "Missing agent spans"
    assert "tool" in semantic_kinds, "Missing tool spans"
    assert "workflow" in semantic_kinds, "Missing workflow spans"

    # Check that each expected function appears in the results
    span_names = [row[0] for row in results]
    assert any("data_agent" in name for name in span_names), (
        f"data_agent not found in {span_names}"
    )
    assert any("fetch_data" in name for name in span_names), (
        f"fetch_data not found in {span_names}"
    )
    assert any("process_data" in name for name in span_names), (
        f"process_data not found in {span_names}"
    )


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_agent_tool_with_version(
    test_org_id: uuid.UUID,
    test_team_id: uuid.UUID,
    test_user_id: uuid.UUID,
):
    """Test that version parameter is tracked correctly for agents and tools."""
    import alphatrion as alpha

    alpha.init(
        org_id=str(test_org_id),
        team_id=str(test_team_id),
        user_id=str(test_user_id),
    )

    experiment_id = None

    @tracing.tool(version=2)
    def versioned_tool() -> str:
        """Tool with version 2."""
        return "versioned result"

    @tracing.agent(version=3)
    def versioned_agent() -> str:
        """Agent with version 3."""
        return versioned_tool()

    @tracing.workflow()
    async def versioned_workflow():
        """Workflow with versioned components."""
        return versioned_agent()

    async with experiment.CraftExperiment.start(name="versioned_tracking_test") as exp:
        experiment_id = exp.id
        task = exp.run(versioned_workflow)
        await task.wait()

    # Verify version attributes are stored
    runtime.init()
    tracestore = runtime.storage_runtime().tracestore
    assert tracestore is not None, "Tracestore not initialized"

    database = tracestore.database
    query = f"""
    SELECT
        SpanName,
        SemanticKind,
        SpanAttributes['traceloop.entity.version'] as version
    FROM {database}.otel_spans
    WHERE ExperimentId = '{experiment_id}'
        AND SemanticKind IN ('agent', 'tool')
    ORDER BY SemanticKind
    """

    spans = tracestore.client.query(query).result_rows
    assert len(spans) >= 2, f"Expected at least 2 spans, got {len(spans)}"

    # Find agent and tool spans by semantic kind
    agent_spans = [s for s in spans if s[1] == "agent"]
    tool_spans = [s for s in spans if s[1] == "tool"]

    assert len(agent_spans) >= 1, (
        f"Expected at least 1 agent span, got {len(agent_spans)}"
    )
    assert len(tool_spans) >= 1, f"Expected at least 1 tool span, got {len(tool_spans)}"

    # Check that function names appear in span names
    agent_span_names = [s[0] for s in agent_spans]
    tool_span_names = [s[0] for s in tool_spans]

    assert any("versioned_agent" in name for name in agent_span_names), (
        f"versioned_agent not found in {agent_span_names}"
    )
    assert any("versioned_tool" in name for name in tool_span_names), (
        f"versioned_tool not found in {tool_span_names}"
    )

    # Verify versions are tracked
    agent_version = agent_spans[0][2]
    tool_version = tool_spans[0][2]

    assert agent_version == "3", (
        f"Agent version not tracked, expected '3', got '{agent_version}'"
    )
    assert tool_version == "2", (
        f"Tool version not tracked, expected '2', got '{tool_version}'"
    )


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_workflow_decorator_tracking(
    test_org_id: uuid.UUID,
    test_team_id: uuid.UUID,
    test_user_id: uuid.UUID,
):
    """Test that @workflow decorator creates spans with correct semantic kind in ClickHouse."""
    import alphatrion as alpha

    alpha.init(
        org_id=str(test_org_id),
        team_id=str(test_team_id),
        user_id=str(test_user_id),
    )

    experiment_id = None

    @tracing.workflow()
    async def data_processing_workflow():
        """A workflow that processes data."""
        return "data processed"

    @tracing.workflow()
    async def notification_workflow():
        """A workflow that sends notifications."""
        return "notifications sent"

    @tracing.workflow()
    async def main_workflow():
        """Main workflow that orchestrates sub-workflows."""
        result1 = await data_processing_workflow()
        result2 = await notification_workflow()
        return result1, result2

    async with experiment.CraftExperiment.start(name="workflow_tracking_test") as exp:
        experiment_id = exp.id
        task = exp.run(main_workflow)
        await task.wait()

    # Query ClickHouse for workflow spans
    runtime.init()
    tracestore = runtime.storage_runtime().tracestore
    assert tracestore is not None, "Tracestore not initialized"

    database = tracestore.database
    query = f"""
    SELECT
        SpanId,
        SpanName,
        SemanticKind,
        TeamId,
        ExperimentId,
        SpanAttributes['traceloop.span.kind'] as traceloop_kind
    FROM {database}.otel_spans
    WHERE ExperimentId = '{experiment_id}'
        AND SemanticKind = 'workflow'
    ORDER BY Timestamp
    """

    spans = tracestore.client.query(query).result_rows
    assert len(spans) >= 3, f"Expected at least 3 workflow spans, got {len(spans)}"

    workflow_names = {span[1] for span in spans}
    assert any("data_processing_workflow" in name for name in workflow_names), (
        f"data_processing_workflow not found in {workflow_names}"
    )
    assert any("notification_workflow" in name for name in workflow_names), (
        f"notification_workflow not found in {workflow_names}"
    )
    assert any("main_workflow" in name for name in workflow_names), (
        f"main_workflow not found in {workflow_names}"
    )

    for span in spans:
        span_id, span_name, semantic_kind, team_id, exp_id, traceloop_kind = span

        assert semantic_kind == "workflow", f"Span {span_id}: wrong semantic kind"
        assert traceloop_kind == "workflow", f"Span {span_id}: wrong traceloop kind"
        assert team_id == str(test_team_id), f"Span {span_id}: wrong team_id"
        assert exp_id == str(experiment_id), f"Span {span_id}: wrong experiment_id"


@pytest.mark.asyncio
@pytest.mark.timeout(60)
async def test_task_decorator_tracking(
    test_org_id: uuid.UUID,
    test_team_id: uuid.UUID,
    test_user_id: uuid.UUID,
):
    """Test that @task decorator creates spans with correct semantic kind in ClickHouse."""
    import alphatrion as alpha

    alpha.init(
        org_id=str(test_org_id),
        team_id=str(test_team_id),
        user_id=str(test_user_id),
    )

    experiment_id = None

    @tracing.task()
    def validate_input(data: str) -> bool:
        """Task that validates input."""
        return len(data) > 0

    @tracing.task()
    def transform_data(data: str) -> str:
        """Task that transforms data."""
        return data.upper()

    @tracing.task()
    def save_result(data: str) -> str:
        """Task that saves result."""
        return f"Saved: {data}"

    @tracing.workflow()
    async def task_workflow():
        """Workflow that uses tasks."""
        is_valid = validate_input("test data")
        if is_valid:
            transformed = transform_data("test data")
            result = save_result(transformed)
            return result
        return "invalid"

    async with experiment.CraftExperiment.start(name="task_tracking_test") as exp:
        experiment_id = exp.id
        task = exp.run(task_workflow)
        await task.wait()

    # Query ClickHouse for task spans
    runtime.init()
    tracestore = runtime.storage_runtime().tracestore
    assert tracestore is not None, "Tracestore not initialized"

    database = tracestore.database
    query = f"""
    SELECT
        SpanId,
        SpanName,
        SemanticKind,
        TeamId,
        ExperimentId,
        SpanAttributes['traceloop.span.kind'] as traceloop_kind
    FROM {database}.otel_spans
    WHERE ExperimentId = '{experiment_id}'
        AND SemanticKind = 'task'
    ORDER BY Timestamp
    """

    spans = tracestore.client.query(query).result_rows
    assert len(spans) == 3, f"Expected 3 task spans, got {len(spans)}"

    task_names = {span[1] for span in spans}
    assert any("validate_input" in name for name in task_names), (
        f"validate_input not found in {task_names}"
    )
    assert any("transform_data" in name for name in task_names), (
        f"transform_data not found in {task_names}"
    )
    assert any("save_result" in name for name in task_names), (
        f"save_result not found in {task_names}"
    )

    for span in spans:
        span_id, span_name, semantic_kind, team_id, exp_id, traceloop_kind = span

        assert semantic_kind == "task", f"Span {span_id}: wrong semantic kind"
        assert traceloop_kind == "task", f"Span {span_id}: wrong traceloop kind"
        assert team_id == str(test_team_id), f"Span {span_id}: wrong team_id"
        assert exp_id == str(experiment_id), f"Span {span_id}: wrong experiment_id"
