# ruff: noqa: PLW0603
import os

from opentelemetry import trace
from traceloop.sdk import Traceloop

from alphatrion import envs
from alphatrion.storage.sqlstore import SQLStore
from alphatrion.storage.tracestore import TraceStore
from alphatrion.tracing.clickhouse_exporter import ClickHouseSpanExporter
from alphatrion.tracing.span_processor import ContextAttributesSpanProcessor

__STORAGE_RUNTIME__ = None


class StorageRuntime:
    _metadb = None
    _tracestore = None
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
            self._tracestore = TraceStore(
                host=os.getenv(envs.CLICKHOUSE_URL, "localhost:8123"),
                database=os.getenv(envs.CLICKHOUSE_DATABASE, "alphatrion_traces"),
                username=os.getenv(envs.CLICKHOUSE_USERNAME, "alphatrion"),
                password=os.getenv(envs.CLICKHOUSE_PASSWORD, "alphatr1on"),
                init_tables=os.getenv(envs.CLICKHOUSE_INIT_TABLES, "false").lower()
                == "true",
            )

            Traceloop.init(
                app_name="alphatrion",
                exporter=ClickHouseSpanExporter(self.tracestore),
                disable_batch=False,  # Enable batching
                telemetry_enabled=False,
            )

            # Add custom span processor to inject context attributes (run_id, etc.)
            # into all spans, including child spans created by instrumented libraries
            tracer_provider = trace.get_tracer_provider()
            tracer_provider.add_span_processor(ContextAttributesSpanProcessor())

        self._inited = True

    @property
    def metadb(self):
        return self._metadb

    @property
    def tracestore(self):
        return self._tracestore


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
