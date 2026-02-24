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
        init_tables: bool = False,
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

        # Create database if it doesn't exist
        self._create_database()

        # Initialize tables if requested
        if init_tables:
            self._create_tables()

    def _create_database(self) -> None:
        """Create the database if it doesn't exist."""
        try:
            self.client.command(f"CREATE DATABASE IF NOT EXISTS {self.database}")
            logger.info(f"Database {self.database} ready")
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            raise

    def _create_tables(self) -> None:
        """Create the otel_spans table if it doesn't exist."""
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {self.database}.otel_spans (
            Timestamp DateTime64(9) CODEC(Delta, ZSTD(1)),
            TraceId String CODEC(ZSTD(1)),
            SpanId String CODEC(ZSTD(1)),
            ParentSpanId String CODEC(ZSTD(1)),
            SpanName LowCardinality(String) CODEC(ZSTD(1)),
            SpanKind LowCardinality(String) CODEC(ZSTD(1)),
            SemanticKind LowCardinality(String) CODEC(ZSTD(1)),
            ServiceName LowCardinality(String) CODEC(ZSTD(1)),
            Duration UInt64 CODEC(ZSTD(1)),
            StatusCode LowCardinality(String) CODEC(ZSTD(1)),
            StatusMessage String CODEC(ZSTD(1)),
            TeamId String CODEC(ZSTD(1)),
            ProjectId String CODEC(ZSTD(1)),
            RunId String CODEC(ZSTD(1)),
            ExperimentId String CODEC(ZSTD(1)),
            SpanAttributes Map(LowCardinality(String), String) CODEC(ZSTD(1)),
            ResourceAttributes Map(LowCardinality(String), String) CODEC(ZSTD(1)),
            Events Nested(
                Timestamp DateTime64(9),
                Name LowCardinality(String),
                Attributes Map(LowCardinality(String), String)
            ) CODEC(ZSTD(1)),
            Links Nested(
                TraceId String,
                SpanId String,
                Attributes Map(LowCardinality(String), String)
            ) CODEC(ZSTD(1)),
            INDEX idx_trace_id TraceId TYPE bloom_filter(0.001) GRANULARITY 1,
            INDEX idx_span_id SpanId TYPE bloom_filter(0.001) GRANULARITY 1,
            INDEX idx_run_id RunId TYPE bloom_filter(0.001) GRANULARITY 1,
            INDEX idx_project_id ProjectId TYPE bloom_filter(0.001) GRANULARITY 1,
            INDEX idx_team_id TeamId TYPE bloom_filter(0.001) GRANULARITY 1,
            INDEX idx_semantic_kind SemanticKind TYPE set(0) GRANULARITY 1,
            INDEX idx_attr_keys mapKeys(SpanAttributes) TYPE bloom_filter(0.01) GRANULARITY 1
        ) ENGINE = MergeTree()
        PARTITION BY toDate(Timestamp)
        ORDER BY (ServiceName, toUnixTimestamp(Timestamp))
        SETTINGS index_granularity = 8192
        """

        try:
            self.client.command(create_table_sql)
            logger.info(f"Table {self.database}.otel_spans ready")
        except Exception as e:
            logger.error(f"Failed to create table: {e}")
            raise

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
                            span.get("TeamId", ""),
                            span.get("ProjectId", ""),
                            span.get("RunId", ""),
                            span.get("ExperimentId", ""),
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
                        "TeamId",
                        "ProjectId",
                        "RunId",
                        "ExperimentId",
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

    def get_spans_by_run_id(self, run_id: uuid.UUID) -> list[dict[str, Any]]:
        """Get all spans for a specific run_id.

        Args:
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
                    TeamId,
                    ProjectId,
                    RunId,
                    ExperimentId,
                    SpanAttributes,
                    ResourceAttributes,
                    Events.Timestamp as EventTimestamps,
                    Events.Name as EventNames,
                    Events.Attributes as EventAttributes,
                    Links.TraceId as LinkTraceIds,
                    Links.SpanId as LinkSpanIds,
                    Links.Attributes as LinkAttributes
                FROM {self.database}.otel_spans
                WHERE RunId = '{run_id}'
                ORDER BY Timestamp ASC
                """

                result = self.client.query(query)
                return list(result.named_results())
            except Exception as e:
                logger.error(f"Failed to get spans by run_id: {e}")
                return []

    def get_llm_spans_by_run_id(self, run_id: uuid.UUID) -> list[dict[str, Any]]:
        """Get all LLM spans for a specific run_id.

        Args:
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
                    TeamId,
                    ProjectId,
                    RunId,
                    ExperimentId,
                    SpanAttributes,
                    ResourceAttributes,
                    Events.Timestamp as EventTimestamps,
                    Events.Name as EventNames,
                    Events.Attributes as EventAttributes,
                    Links.TraceId as LinkTraceIds,
                    Links.SpanId as LinkSpanIds,
                    Links.Attributes as LinkAttributes
                FROM {self.database}.otel_spans
                WHERE RunId = '{run_id}' AND SemanticKind = 'llm'
                ORDER BY Timestamp ASC
                """

                result = self.client.query(query)
                return list(result.named_results())
            except Exception as e:
                logger.error(f"Failed to get traces by run_id: {e}")
                return []

    def get_llm_spans_by_exp_id(self, exp_id: uuid.UUID) -> list[dict[str, Any]]:
        """Get all LLM spans for a specific experiment_id.

        Args:
            exp_id: The experiment ID to filter by

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
                    TeamId,
                    ProjectId,
                    RunId,
                    ExperimentId,
                    SpanAttributes,
                    ResourceAttributes,
                    Events.Timestamp as EventTimestamps,
                    Events.Name as EventNames,
                    Events.Attributes as EventAttributes,
                    Links.TraceId as LinkTraceIds,
                    Links.SpanId as LinkSpanIds,
                    Links.Attributes as LinkAttributes
                FROM {self.database}.otel_spans
                WHERE ExperimentId = '{exp_id}' AND SemanticKind = 'llm'
                ORDER BY Timestamp ASC
                """

                result = self.client.query(query)
                return list(result.named_results())
            except Exception as e:
                logger.error(f"Failed to get spans by exp_id: {e}")
                return []

    def get_daily_token_usage(
        self, team_id: uuid.UUID, days: int = 30
    ) -> list[dict[str, Any]]:
        """Get daily token usage from LLM calls for a team.

        Args:
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
                WHERE TeamId = '{team_id}'
                  AND Timestamp >= now() - INTERVAL {days} DAY
                  AND SemanticKind = 'llm'
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

    def close(self) -> None:
        """Close the ClickHouse connection."""
        try:
            self.client.close()
            logger.debug("ClickHouse client closed")
        except Exception as e:
            logger.error(f"Failed to close ClickHouse client: {e}")
