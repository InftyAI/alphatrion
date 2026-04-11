# ruff: noqa: PLW0603
import logging
import os

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from traceloop.sdk import Traceloop

from alphatrion import envs
from alphatrion.artifact.artifact import Artifact
from alphatrion.storage.sqlstore import SQLStore
from alphatrion.storage.tracestore import TraceStore
from alphatrion.tracing.clickhouse_exporter import ClickHouseSpanExporter
from alphatrion.tracing.cost_enrichment_processor import CostEnrichmentProcessor
from alphatrion.tracing.prometheus_exporter import PrometheusExporter
from alphatrion.tracing.span_processor import ContextAttributesSpanProcessor

__STORAGE_RUNTIME__ = None


class StorageRuntime:
    _metadb = None
    _tracestore = None
    _artifact = None
    _inited = False

    def __init__(self):
        if self._inited:
            return

        self._metadb = SQLStore(
            os.getenv(envs.METADATA_DB_URL),
            init_tables=os.getenv(envs.METADATA_INIT_TABLES, "false").lower() == "true",
        )

        # Disable tracing by default now
        if os.getenv(envs.ENABLE_TRACING, "false").lower() == "true":
            try:
                self._tracestore = TraceStore(
                    host=os.getenv(envs.CLICKHOUSE_URL, "localhost:8123"),
                    database=os.getenv(envs.CLICKHOUSE_DATABASE, "alphatrion_traces"),
                    username=os.getenv(envs.CLICKHOUSE_USERNAME, "alphatrion"),
                    password=os.getenv(envs.CLICKHOUSE_PASSWORD, "alphatr1on"),
                )
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Failed to initialize ClickHouse TraceStore: {e}. "
                    "Tracing will be disabled. To enable tracing, ensure ClickHouse is running "
                    "or set ALPHATRION_ENABLE_TRACING=false to suppress this warning."
                )
                self._tracestore = None

            # Only initialize tracing components if TraceStore was successfully created
            if self._tracestore is not None:
                enable_batch = (
                    os.getenv(envs.CLICKHOUSE_ENABLE_BATCH, "true").lower() == "true"
                )
                Traceloop.init(
                    app_name="alphatrion",
                    exporter=ClickHouseSpanExporter(self.tracestore),
                    disable_batch=not enable_batch,
                    telemetry_enabled=False,
                )

                # Add custom span processors
                tracer_provider = trace.get_tracer_provider()

                # 1. Context attributes processor - injects context (run_id, etc.) into all spans
                tracer_provider.add_span_processor(ContextAttributesSpanProcessor())

                # 2. Cost enrichment processor - calculates costs from tokens and adds to span attributes
                # This runs early so downstream processors/exporters can access cost data
                tracer_provider.add_span_processor(CostEnrichmentProcessor())

                # 3. Add Prometheus exporter if enabled
                if (
                    os.getenv(envs.ENABLE_PROMETHEUS_EXPORTER, "false").lower()
                    == "true"
                ):
                    pushgateway_url = os.getenv(
                        envs.PROMETHEUS_PUSHGATEWAY_URL, "localhost:9091"
                    )
                    job_name = os.getenv(envs.PROMETHEUS_JOB_NAME, "alphatrion")

                    prometheus_exporter = PrometheusExporter(
                        pushgateway_url=pushgateway_url,
                        job_name=job_name,
                    )
                    # Use BatchSpanProcessor for better performance
                    tracer_provider.add_span_processor(
                        BatchSpanProcessor(prometheus_exporter)
                    )

        artifact_insecure = os.getenv(envs.ARTIFACT_INSECURE, "false").lower() == "true"
        if artifact_storage_enabled():
            self._artifact = Artifact(insecure=artifact_insecure)

        self._inited = True

    @property
    def metadb(self):
        return self._metadb

    @property
    def tracestore(self):
        return self._tracestore

    def flush(self):
        if self._tracestore:
            tracer_provider = trace.get_tracer_provider()
            if isinstance(tracer_provider, TracerProvider):
                tracer_provider.force_flush(timeout_millis=5000)

    @property
    def artifact(self):
        return self._artifact


def init():
    """
    Initialize the Storage runtime environment.
    """

    global __STORAGE_RUNTIME__
    if __STORAGE_RUNTIME__ is None:
        __STORAGE_RUNTIME__ = StorageRuntime()


def storage_runtime() -> StorageRuntime:
    if __STORAGE_RUNTIME__ is None:
        raise RuntimeError("StorageRuntime is not initialized. Call init() first.")
    return __STORAGE_RUNTIME__


def artifact_storage_enabled() -> bool:
    return os.getenv(envs.ENABLE_ARTIFACT_STORAGE, "true").lower() == "true"
