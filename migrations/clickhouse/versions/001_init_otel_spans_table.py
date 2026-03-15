"""Create initial otel_spans table.

Revision: 001
Created: 2026-03-15
"""
import logging
import os

import clickhouse_connect

from migrations.clickhouse.runner import Migration

logger = logging.getLogger(__name__)


class InitOtelSpansTable(Migration):
    """Create the base otel_spans table for OpenTelemetry traces.

    Supports both single-node (MergeTree) and cluster (ReplicatedMergeTree) setups.
    """

    version = "001"
    name = "init_otel_spans_table"

    def upgrade(self, client: clickhouse_connect.driver.Client, database: str) -> None:
        """Create otel_spans table with full schema."""
        logger.info("Creating otel_spans table")

        # Check if cluster mode is enabled
        cluster_name = os.getenv("ALPHATRION_CLICKHOUSE_CLUSTER_NAME")

        if cluster_name:
            # Cluster mode: Use ReplicatedMergeTree with ON CLUSTER
            logger.info(f"Using cluster mode with cluster: {cluster_name}")
            engine = f"ReplicatedMergeTree('/clickhouse/tables/{{shard}}/otel_spans', '{{replica}}')"
            on_cluster = f"ON CLUSTER {cluster_name}"
        else:
            # Single-node mode: Use MergeTree
            logger.info("Using single-node mode")
            engine = "MergeTree()"
            on_cluster = ""

        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {database}.otel_spans {on_cluster} (
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
            INDEX idx_team_id TeamId TYPE bloom_filter(0.001) GRANULARITY 1,
            INDEX idx_semantic_kind SemanticKind TYPE set(0) GRANULARITY 1,
            INDEX idx_attr_keys mapKeys(SpanAttributes) TYPE bloom_filter(0.01) GRANULARITY 1
        ) ENGINE = {engine}
        PARTITION BY toDate(Timestamp)
        ORDER BY (ServiceName, toUnixTimestamp(Timestamp))
        SETTINGS index_granularity = 8192
        """

        client.command(create_table_sql)
        logger.info(f"✓ Table {database}.otel_spans created")

    def downgrade(self, client: clickhouse_connect.driver.Client, database: str) -> None:
        """Drop otel_spans table."""
        logger.info("Dropping otel_spans table")

        # Check if cluster mode is enabled
        cluster_name = os.getenv("ALPHATRION_CLICKHOUSE_CLUSTER_NAME")
        on_cluster = f"ON CLUSTER {cluster_name}" if cluster_name else ""

        client.command(f"DROP TABLE IF EXISTS {database}.otel_spans {on_cluster}")
        logger.info("✓ Table dropped")


# Export migration instance
migration = InitOtelSpansTable()
