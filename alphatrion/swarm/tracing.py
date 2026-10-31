"""
Tracing, with OpenTelemetry and OpenInference's conventions: every graph run,
node attempt and model request is a span, so a model call nests under the
node and the run that sent it. setup() picks where spans go, with exporters:
HostExporter for a file of JSON lines, DatabaseExporter for SQLite, or any
OpenTelemetry exporter, e.g. OTLP to Phoenix, Langfuse or Jaeger. Without
setup(), spans go to the global OpenTelemetry provider, a no-op unless the
application configures one.

Model requests are spans of OpenInference's LLM kind, with the model, the
request and the response, whatever the client. instrument=True also traces
the Anthropic and OpenAI SDKs themselves, with OpenInference's instrumentors,
nesting their spans under the request's.
"""

import json
import sqlite3
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from openinference.semconv.trace import OpenInferenceSpanKindValues, SpanAttributes
from opentelemetry import trace
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export import (
    SimpleSpanProcessor,
    SpanExporter,
    SpanExportResult,
)

NAME = "alphatrion.swarm"
_provider: TracerProvider | None = None

LLM = OpenInferenceSpanKindValues.LLM.value
CHAIN = OpenInferenceSpanKindValues.CHAIN.value
KIND = SpanAttributes.OPENINFERENCE_SPAN_KIND


def setup(*exporters: SpanExporter, instrument: bool = False) -> TracerProvider:
    """Send swarm's spans to the exporters, and the SDKs' too if instrument.
    Calling it again replaces them."""
    global _provider
    if _provider is not None:
        _provider.shutdown()
    _provider = TracerProvider()
    for exporter in exporters:
        _provider.add_span_processor(SimpleSpanProcessor(exporter))
    if instrument:
        _instrument(_provider)
    return _provider


def tracer() -> trace.Tracer:
    if _provider is not None:
        return _provider.get_tracer(NAME)
    return trace.get_tracer(NAME)


def _instrument(provider: TracerProvider) -> None:
    for module, name in (
        ("openinference.instrumentation.anthropic", "AnthropicInstrumentor"),
        ("openinference.instrumentation.openai", "OpenAIInstrumentor"),
    ):
        try:
            instrumentor = getattr(__import__(module, fromlist=[name]), name)()
        except ImportError:
            continue
        instrumentor.uninstrument()
        instrumentor.instrument(tracer_provider=provider)


def span_record(span: ReadableSpan) -> dict[str, Any]:
    """A span as plain JSON: its ids, name, times, status, attributes and
    events."""
    context = span.get_span_context()
    return {
        "trace_id": format(context.trace_id, "032x"),
        "span_id": format(context.span_id, "016x"),
        "parent_id": format(span.parent.span_id, "016x") if span.parent else None,
        "name": span.name,
        "start": span.start_time,
        "end": span.end_time,
        "status": span.status.status_code.name,
        "attributes": dict(span.attributes or {}),
        "events": [
            {
                "name": e.name,
                "time": e.timestamp,
                "attributes": dict(e.attributes or {}),
            }
            for e in span.events
        ],
    }


class HostExporter(SpanExporter):
    """Spans to a file on this machine, one span per line as JSON, appended
    as they end, so a crashed run keeps what it traced."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        with self.path.open("a") as f:
            for span in spans:
                f.write(json.dumps(span_record(span), default=str) + "\n")
        return SpanExportResult.SUCCESS

    def records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        return [json.loads(line) for line in self.path.read_text().splitlines() if line]


class DatabaseExporter(SpanExporter):
    """Spans to a SQLite database: each as JSON, with its trace, parent, name,
    node and model as indexed columns, e.g. to count requests by model."""

    def __init__(self, path: str | Path):
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS spans (span_id TEXT PRIMARY KEY, "
            "trace_id TEXT, parent_id TEXT, name TEXT, node TEXT, model TEXT, "
            "start INTEGER, record TEXT)"
        )
        for column in ("trace_id", "node", "model"):
            self._db.execute(
                f"CREATE INDEX IF NOT EXISTS spans_{column} ON spans ({column})"
            )
        self._db.commit()

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        for span in spans:
            record = span_record(span)
            attributes = record["attributes"]
            self._db.execute(
                "INSERT OR REPLACE INTO spans VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    record["span_id"],
                    record["trace_id"],
                    record["parent_id"],
                    record["name"],
                    attributes.get("swarm.node"),
                    attributes.get(SpanAttributes.LLM_MODEL_NAME),
                    record["start"],
                    json.dumps(record, default=str),
                ),
            )
        self._db.commit()
        return SpanExportResult.SUCCESS

    def query(self, sql: str, *args: Any) -> list[tuple]:
        return self._db.execute(sql, args).fetchall()

    def records(self) -> list[dict[str, Any]]:
        rows = self._db.execute("SELECT record FROM spans ORDER BY start")
        return [json.loads(row[0]) for row in rows]

    def shutdown(self) -> None:
        self._db.close()
