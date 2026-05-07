"""No-op Span Exporter.

Accepts and discards spans. Used when the OTel pipeline is needed
(e.g. for Prometheus cost export) but ClickHouse tracing is disabled.
"""

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult


class NoOpSpanExporter(SpanExporter):

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        return True
