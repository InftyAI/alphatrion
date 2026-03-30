# ruff: noqa: E501

import logging
import threading
import uuid
from typing import Any

import clickhouse_connect

logger = logging.getLogger(__name__)


class TraceStore:
    """ClickHouse-backed storage for OpenTelemetry traces and spans."""

    def __init__(
        self,
        host: str,
        database: str,
        username: str,
        password: str,
    ):
        """Initialize ClickHouse TraceStore.

        Args:
            host: ClickHouse server host (e.g., "localhost:8123" or "http://localhost:8123")
            database: Database name
            username: Database username
            password: Database password
            init_tables: If True, create tables on initialization
        """
        self.database = database
        self._lock = threading.Lock()  # Protect concurrent access to ClickHouse client

        # Parse host and port, stripping protocol if present
        # Handle URLs like "http://localhost:8123" or "localhost:8123"
        clean_host = host
        if "://" in clean_host:
            # Remove protocol (http:// or https://)
            clean_host = clean_host.split("://", 1)[1]

        # Now split by : to get host and port
        host_parts = clean_host.split(":")
        ch_host = host_parts[0]
        ch_port = int(host_parts[1]) if len(host_parts) > 1 else 8123

        # Create ClickHouse client
        self.client = clickhouse_connect.get_client(
            host=ch_host,
            port=ch_port,
            username=username,
            password=password,
        )

    def insert_spans(self, spans: list[dict[str, Any]]) -> None:
        """Insert spans into ClickHouse.

        Args:
            spans: List of span dictionaries with OpenTelemetry fields
        """
        if not spans:
            return

        with self._lock:  # Protect concurrent access to ClickHouse client
            try:
                # Prepare data for insertion
                data = []
                for span in spans:
                    data.append(
                        (
                            span.get("Timestamp"),
                            span.get("TraceId", ""),
                            span.get("SpanId", ""),
                            span.get("ParentSpanId", ""),
                            span.get("SpanName", ""),
                            span.get("SpanKind", ""),
                            span.get("SemanticKind", ""),
                            span.get("ServiceName", ""),
                            span.get("Duration", 0),
                            span.get("StatusCode", ""),
                            span.get("StatusMessage", ""),
                            span.get("OrgId", ""),
                            span.get("TeamId", ""),
                            span.get("UserId", ""),
                            span.get("RunId", ""),
                            span.get("ExperimentId", ""),
                            span.get("SessionId", ""),
                            span.get("AgentId", ""),
                            span.get("AgentType", ""),
                            span.get("SpanAttributes", {}),
                            span.get("ResourceAttributes", {}),
                            span.get("Events.Timestamp", []),
                            span.get("Events.Name", []),
                            span.get("Events.Attributes", []),
                            span.get("Links.TraceId", []),
                            span.get("Links.SpanId", []),
                            span.get("Links.Attributes", []),
                        )
                    )

                # Insert into ClickHouse
                self.client.insert(
                    f"{self.database}.otel_spans",
                    data,
                    column_names=[
                        "Timestamp",
                        "TraceId",
                        "SpanId",
                        "ParentSpanId",
                        "SpanName",
                        "SpanKind",
                        "SemanticKind",
                        "ServiceName",
                        "Duration",
                        "StatusCode",
                        "StatusMessage",
                        "OrgId",
                        "TeamId",
                        "UserId",
                        "RunId",
                        "ExperimentId",
                        "SessionId",
                        "AgentId",
                        "AgentType",
                        "SpanAttributes",
                        "ResourceAttributes",
                        "Events.Timestamp",
                        "Events.Name",
                        "Events.Attributes",
                        "Links.TraceId",
                        "Links.SpanId",
                        "Links.Attributes",
                    ],
                )
                logger.debug(f"Inserted {len(spans)} spans into ClickHouse")
            except Exception as e:
                logger.error(f"Failed to insert spans: {e}")
                # Don't raise - we don't want to crash the application if tracing fails

    def get_spans_by_run_id(
        self, org_id: uuid.UUID, team_id: uuid.UUID, run_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Get all spans for a specific run_id.

        Args:
            org_id: The organization ID for efficient index usage
            team_id: The team ID for efficient index usage
            run_id: The run ID to filter by

        Returns:
            List of span dictionaries from ClickHouse
        """
        with self._lock:  # Protect concurrent access to ClickHouse client
            try:
                query = f"""
                SELECT
                    Timestamp,
                    TraceId,
                    SpanId,
                    ParentSpanId,
                    SpanName,
                    SpanKind,
                    SemanticKind,
                    ServiceName,
                    Duration,
                    StatusCode,
                    StatusMessage,
                    OrgId,
                    TeamId,
                    UserId,
                    RunId,
                    ExperimentId,
                    SessionId,
                    AgentId,
                    AgentType,
                    SpanAttributes,
                    ResourceAttributes,
                    Events.Timestamp as EventTimestamps,
                    Events.Name as EventNames,
                    Events.Attributes as EventAttributes,
                    Links.TraceId as LinkTraceIds,
                    Links.SpanId as LinkSpanIds,
                    Links.Attributes as LinkAttributes
                FROM {self.database}.otel_spans
                WHERE OrgId = '{org_id}' AND TeamId = '{team_id}' AND RunId = '{run_id}'
                ORDER BY Timestamp ASC
                """

                result = self.client.query(query)
                return list(result.named_results())
            except Exception as e:
                logger.error(f"Failed to get spans by run_id: {e}")
                return []

    def get_llm_spans_by_run_id(
        self, org_id: uuid.UUID, team_id: uuid.UUID, run_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Get all LLM spans for a specific run_id.

        Args:
            org_id: The organization ID for efficient index usage
            team_id: The team ID for efficient index usage
            run_id: The run ID to filter by

        Returns:
            List of LLM span dictionaries
        """
        with self._lock:  # Protect concurrent access to ClickHouse client
            try:
                query = f"""
                SELECT
                    Timestamp,
                    TraceId,
                    SpanId,
                    ParentSpanId,
                    SpanName,
                    SpanKind,
                    SemanticKind,
                    ServiceName,
                    Duration,
                    StatusCode,
                    StatusMessage,
                    OrgId,
                    TeamId,
                    UserId,
                    RunId,
                    ExperimentId,
                    SessionId,
                    AgentId,
                    AgentType,
                    SpanAttributes,
                    ResourceAttributes,
                    Events.Timestamp as EventTimestamps,
                    Events.Name as EventNames,
                    Events.Attributes as EventAttributes,
                    Links.TraceId as LinkTraceIds,
                    Links.SpanId as LinkSpanIds,
                    Links.Attributes as LinkAttributes
                FROM {self.database}.otel_spans
                WHERE OrgId = '{org_id}' AND TeamId = '{team_id}' AND RunId = '{run_id}'
                ORDER BY Timestamp ASC
                """

                result = self.client.query(query)
                return list(result.named_results())
            except Exception as e:
                logger.error(f"Failed to get traces by run_id: {e}")
                return []

    def get_spans_by_session_id(
        self, org_id: uuid.UUID, team_id: uuid.UUID, session_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Get all spans for a specific session_id (agent runs).

        Args:
            org_id: The organization ID for efficient index usage
            team_id: The team ID for efficient index usage
            session_id: The session ID to filter by

        Returns:
            List of span dictionaries from ClickHouse
        """
        with self._lock:
            try:
                query = f"""
                SELECT
                    Timestamp,
                    TraceId,
                    SpanId,
                    ParentSpanId,
                    SpanName,
                    SpanKind,
                    SemanticKind,
                    ServiceName,
                    Duration,
                    StatusCode,
                    StatusMessage,
                    OrgId,
                    TeamId,
                    UserId,
                    RunId,
                    ExperimentId,
                    SessionId,
                    AgentId,
                    AgentType,
                    SpanAttributes,
                    ResourceAttributes,
                    Events.Timestamp as EventTimestamps,
                    Events.Name as EventNames,
                    Events.Attributes as EventAttributes,
                    Links.TraceId as LinkTraceIds,
                    Links.SpanId as LinkSpanIds,
                    Links.Attributes as LinkAttributes
                FROM {self.database}.otel_spans
                WHERE OrgId = '{org_id}' AND TeamId = '{team_id}' AND SessionId = '{session_id}'
                ORDER BY Timestamp ASC
                """

                result = self.client.query(query)
                return list(result.named_results())
            except Exception as e:
                logger.error(f"Failed to get spans by session_id: {e}")
                return []

    def get_llm_spans_by_exp_id(
        self, org_id: uuid.UUID, team_id: uuid.UUID, experiment_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Get all LLM spans for a specific experiment_id.

        Args:
            org_id: The organization ID for efficient index usage
            team_id: The team ID for efficient index usage
            experiment_id: The experiment ID to filter by

        Returns:
            List of LLM span dictionaries
        """
        with self._lock:  # Protect concurrent access to ClickHouse client
            try:
                query = f"""
                SELECT
                    Timestamp,
                    TraceId,
                    SpanId,
                    ParentSpanId,
                    SpanName,
                    SpanKind,
                    SemanticKind,
                    ServiceName,
                    Duration,
                    StatusCode,
                    StatusMessage,
                    OrgId,
                    TeamId,
                    UserId,
                    RunId,
                    ExperimentId,
                    SessionId,
                    AgentId,
                    AgentType,
                    SpanAttributes,
                    ResourceAttributes,
                    Events.Timestamp as EventTimestamps,
                    Events.Name as EventNames,
                    Events.Attributes as EventAttributes,
                    Links.TraceId as LinkTraceIds,
                    Links.SpanId as LinkSpanIds,
                    Links.Attributes as LinkAttributes
                FROM {self.database}.otel_spans
                WHERE OrgId = '{org_id}' AND TeamId = '{team_id}' AND ExperimentId = '{experiment_id}'
                ORDER BY Timestamp ASC
                """

                result = self.client.query(query)
                return list(result.named_results())
            except Exception as e:
                logger.error(f"Failed to get spans by exp_id: {e}")
                return []

    def get_llm_tokens_by_team_id(
        self, org_id: uuid.UUID, team_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Get all LLM spans for a specific team_id.

        Args:
            org_id: The organization ID to filter by
            team_id: The team ID to filter by
        Returns:
            List of LLM span dictionaries
        """
        with self._lock:
            try:
                query = f"""
                SELECT
                    SUM(toInt64OrZero(SpanAttributes['llm.usage.total_tokens'])) as total_tokens,
                    SUM(toInt64OrZero(SpanAttributes['gen_ai.usage.input_tokens'])) as input_tokens,
                    SUM(toInt64OrZero(SpanAttributes['gen_ai.usage.output_tokens'])) as output_tokens
                FROM {self.database}.otel_spans
                WHERE OrgId = '{org_id}' AND TeamId = '{team_id}'
                """

                result = self.client.query(query)
                # Convert date to string format and ensure integers
                return [
                    {
                        "total_tokens": int(row["total_tokens"]),
                        "input_tokens": int(row["input_tokens"]),
                        "output_tokens": int(row["output_tokens"]),
                    }
                    for row in result.named_results()
                ]
            except Exception as e:
                logger.error(f"Failed to get daily token usage: {e}")
                return []

    def get_llm_tokens_by_agent_id(
        self, org_id: uuid.UUID, team_id: uuid.UUID, agent_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Get aggregated LLM token usage for a specific agent.

        Args:
            org_id: The organization ID to filter by
            team_id: The team ID to filter by
            agent_id: The agent ID to filter by
        Returns:
            List with one dict containing total_tokens, input_tokens, output_tokens
        """
        with self._lock:
            try:
                query = f"""
                SELECT
                    SUM(toInt64OrZero(SpanAttributes['llm.usage.total_tokens'])) as total_tokens,
                    SUM(toInt64OrZero(SpanAttributes['gen_ai.usage.input_tokens'])) as input_tokens,
                    SUM(toInt64OrZero(SpanAttributes['gen_ai.usage.output_tokens'])) as output_tokens
                FROM {self.database}.otel_spans
                WHERE OrgId = '{org_id}' AND TeamId = '{team_id}' AND AgentId = '{agent_id}'
                """

                result = self.client.query(query)
                return [
                    {
                        "total_tokens": int(row["total_tokens"]),
                        "input_tokens": int(row["input_tokens"]),
                        "output_tokens": int(row["output_tokens"]),
                    }
                    for row in result.named_results()
                ]
            except Exception as e:
                logger.error(f"Failed to get agent token usage: {e}")
                return []

    def get_llm_tokens_by_session_id(
        self, org_id: uuid.UUID, team_id: uuid.UUID, session_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Get aggregated LLM token usage for a specific session.

        Args:
            org_id: The organization ID to filter by
            team_id: The team ID to filter by
            session_id: The session ID to filter by
        Returns:
            List with one dict containing total_tokens, input_tokens, output_tokens
        """
        with self._lock:
            try:
                query = f"""
                SELECT
                    SUM(toInt64OrZero(SpanAttributes['llm.usage.total_tokens'])) as total_tokens,
                    SUM(toInt64OrZero(SpanAttributes['gen_ai.usage.input_tokens'])) as input_tokens,
                    SUM(toInt64OrZero(SpanAttributes['gen_ai.usage.output_tokens'])) as output_tokens
                FROM {self.database}.otel_spans
                WHERE OrgId = '{org_id}' AND TeamId = '{team_id}' AND SessionId = '{session_id}'
                """

                result = self.client.query(query)
                return [
                    {
                        "total_tokens": int(row["total_tokens"]),
                        "input_tokens": int(row["input_tokens"]),
                        "output_tokens": int(row["output_tokens"]),
                    }
                    for row in result.named_results()
                ]
            except Exception as e:
                logger.error(f"Failed to get session token usage: {e}")
                return []

    def get_token_distribution_by_semantic_kind(
        self, org_id: uuid.UUID, team_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Get token usage distribution grouped by semantic kind.

        Args:
            org_id: The organization ID to filter by
            team_id: The team ID to filter by

        Returns:
            List of dicts with keys: semantic_kind, total_tokens, input_tokens, output_tokens
        """
        with self._lock:
            try:
                query = f"""
                SELECT
                    SemanticKind as semantic_kind,
                    SUM(toInt64OrZero(SpanAttributes['llm.usage.total_tokens'])) as total_tokens,
                    SUM(toInt64OrZero(SpanAttributes['gen_ai.usage.input_tokens'])) as input_tokens,
                    SUM(toInt64OrZero(SpanAttributes['gen_ai.usage.output_tokens'])) as output_tokens
                FROM {self.database}.otel_spans
                WHERE OrgId = '{org_id}' AND TeamId = '{team_id}'
                GROUP BY SemanticKind
                ORDER BY total_tokens DESC
                """

                result = self.client.query(query)
                return [
                    {
                        "semantic_kind": row["semantic_kind"],
                        "total_tokens": int(row["total_tokens"]),
                        "input_tokens": int(row["input_tokens"]),
                        "output_tokens": int(row["output_tokens"]),
                    }
                    for row in result.named_results()
                ]
            except Exception as e:
                logger.error(f"Failed to get token distribution: {e}")
                return []

    def get_model_distributions_by_team_id(
        self, org_id: uuid.UUID, team_id: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Get model distribution (count of requests per model) for a specific team.

        Args:
            org_id: The organization ID to filter by
            team_id: The team ID to filter by

        Returns:
            List of dicts with keys: model, count
        """
        with self._lock:
            try:
                query = f"""
                SELECT
                    coalesce(
                        SpanAttributes['gen_ai.request.model'],
                        SpanAttributes['gen_ai.response.model'],
                        'unknown'
                    ) as model,
                    COUNT(*) as count
                FROM {self.database}.otel_spans
                WHERE OrgId = '{org_id}' AND TeamId = '{team_id}'
                    AND SemanticKind IN ('llm', 'thinking', 'text-generation', 'tool')
                GROUP BY model
                ORDER BY count DESC
                """

                result = self.client.query(query)
                return [
                    {
                        "model": row["model"],
                        "count": int(row["count"]),
                    }
                    for row in result.named_results()
                ]
            except Exception as e:
                logger.error(f"Failed to get model distributions: {e}")
                return []

    def get_daily_token_usage(
        self, org_id: uuid.UUID, team_id: uuid.UUID, days: int = 30
    ) -> list[dict[str, Any]]:
        """Get daily token usage from LLM calls for a team.

        Args:
            org_id: The organization ID to filter by
            team_id: The team ID to filter by
            days: Number of days to look back (default: 30)

        Returns:
            List of dicts with keys: date, total_tokens, input_tokens, output_tokens
        """
        with self._lock:
            try:
                query = f"""
                SELECT
                    toDate(Timestamp) as date,
                    SUM(toInt64OrZero(SpanAttributes['llm.usage.total_tokens'])) as total_tokens,
                    SUM(toInt64OrZero(SpanAttributes['gen_ai.usage.input_tokens'])) as input_tokens,
                    SUM(toInt64OrZero(SpanAttributes['gen_ai.usage.output_tokens'])) as output_tokens
                FROM {self.database}.otel_spans
                WHERE OrgId = '{org_id}' AND TeamId = '{team_id}'
                  AND Timestamp >= now() - INTERVAL {days} DAY
                GROUP BY date
                ORDER BY date ASC
                """

                result = self.client.query(query)
                # Convert date to string format and ensure integers
                return [
                    {
                        "date": row["date"].strftime("%Y-%m-%d"),
                        "total_tokens": int(row["total_tokens"]),
                        "input_tokens": int(row["input_tokens"]),
                        "output_tokens": int(row["output_tokens"]),
                    }
                    for row in result.named_results()
                ]
            except Exception as e:
                logger.error(f"Failed to get daily token usage: {e}")
                return []

    def get_trace_stats_by_exp_id(
        self, org_id: uuid.UUID, team_id: uuid.UUID, exp_id: uuid.UUID
    ) -> dict[str, int]:
        """Get trace statistics (success/error counts) for a specific experiment_id.

        Args:
            org_id: The organization ID to filter by
            team_id: The team ID to filter by
            exp_id: The experiment ID to filter by

        Returns:
            Dict with keys: total_spans, success_spans, error_spans
        """
        with self._lock:
            try:
                query = f"""
                SELECT
                    COUNT(*) as total_spans,
                    countIf(StatusCode = 'OK' OR StatusCode = 'UNSET') as success_spans,
                    countIf(StatusCode = 'ERROR') as error_spans
                FROM {self.database}.otel_spans
                WHERE OrgId = '{org_id}' AND TeamId = '{team_id}' AND ExperimentId = '{exp_id}'
                """

                result = self.client.query(query)
                rows = list(result.named_results())
                if rows and len(rows) > 0:
                    row = rows[0]
                    return {
                        "total_spans": int(row["total_spans"]),
                        "success_spans": int(row["success_spans"]),
                        "error_spans": int(row["error_spans"]),
                    }
                return {"total_spans": 0, "success_spans": 0, "error_spans": 0}
            except Exception as e:
                logger.error(f"Failed to get trace stats by exp_id: {e}")
                return {"total_spans": 0, "success_spans": 0, "error_spans": 0}

    def close(self) -> None:
        """Close the ClickHouse connection."""
        try:
            self.client.close()
            logger.debug("ClickHouse client closed")
        except Exception as e:
            logger.error(f"Failed to close ClickHouse client: {e}")
