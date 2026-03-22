import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from opentelemetry.trace import StatusCode

from alphatrion.storage.tracestore import TraceStore

logger = logging.getLogger(__name__)


class ClickHouseSpanExporter(SpanExporter):
    """Custom OpenTelemetry SpanExporter that writes to ClickHouse."""

    def __init__(self, trace_store: TraceStore):
        """Initialize the ClickHouse span exporter.

        Args:
            trace_store: TraceStore instance for ClickHouse operations
        """
        self.trace_store = trace_store

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        """Export spans to ClickHouse.

        Args:
            spans: Sequence of ReadableSpan objects from OpenTelemetry

        Returns:
            SpanExportResult indicating success or failure
        """
        if not spans:
            return SpanExportResult.SUCCESS

        try:
            # Filter spans based on context:
            # - For agent runs (has session_id): save ALL spans
            # - For experiments (no session_id): save only traceloop workflow/task spans
            filtered_spans = []
            for span in spans:
                if not span.attributes:
                    continue

                # Check if this is an agent run (has session_id attribute)
                session_id = span.attributes.get("session_id")
                is_agent_run = session_id is not None and session_id != ""

                if is_agent_run:
                    # Agent run: save ALL spans (HTTP, DB, LLM, etc.)
                    filtered_spans.append(span)
                elif "traceloop.workflow.name" in span.attributes:
                    # Experiment run: only save traceloop workflow/task spans
                    filtered_spans.append(span)

            if not filtered_spans:
                return SpanExportResult.SUCCESS

            # Convert OpenTelemetry spans to ClickHouse format
            ch_spans = [self._convert_span(span) for span in filtered_spans]

            # Insert into ClickHouse
            self.trace_store.insert_spans(ch_spans)

            return SpanExportResult.SUCCESS
        except Exception as e:
            logger.error(f"Failed to export spans to ClickHouse: {e}", exc_info=True)
            return SpanExportResult.FAILURE

    def _convert_span(self, span: ReadableSpan) -> dict[str, Any]:
        """Convert OpenTelemetry ReadableSpan to ClickHouse format.

        Args:
            span: ReadableSpan from OpenTelemetry

        Returns:
            Dictionary with ClickHouse column values
        """
        # Convert trace_id and span_id to hex strings
        trace_id = format(span.context.trace_id, "032x")
        span_id = format(span.context.span_id, "016x")
        parent_span_id = format(span.parent.span_id, "016x") if span.parent else ""

        # Convert timestamps (nanoseconds to DateTime64(9))
        timestamp = self._nano_to_datetime(span.start_time)
        duration = span.end_time - span.start_time if span.end_time else 0

        # Convert SpanKind to string
        span_kind_map = {
            1: "INTERNAL",
            2: "SERVER",
            3: "CLIENT",
            4: "PRODUCER",
            5: "CONSUMER",
        }
        span_kind = span_kind_map.get(span.kind.value, "INTERNAL")

        # Convert StatusCode to string
        status_code_map = {
            StatusCode.UNSET: "UNSET",
            StatusCode.OK: "OK",
            StatusCode.ERROR: "ERROR",
        }
        status_code = status_code_map.get(span.status.status_code, "UNSET")
        status_message = span.status.description or ""

        # Extract service name from resource attributes
        resource_attrs = {}
        service_name = "unknown_service"
        if span.resource:
            resource_attrs = (
                dict(span.resource.attributes) if span.resource.attributes else {}
            )
            # Convert all values to strings for ClickHouse Map(String, String)
            resource_attrs = {k: str(v) for k, v in resource_attrs.items()}
            service_name = resource_attrs.get("service.name", "unknown_service")

        # Convert span attributes to string map
        span_attributes = {}
        if span.attributes:
            span_attributes = {k: str(v) for k, v in span.attributes.items()}

        # Extract core identifiers from span attributes
        team_id = span_attributes.get("team_id", "")
        user_id = span_attributes.get("user_id", "")
        run_id = span_attributes.get("run_id", "")
        experiment_id = span_attributes.get("experiment_id", "")
        session_id = span_attributes.get("session_id", "")
        agent_id = span_attributes.get("agent_id", "")
        agent_type = span_attributes.get("agent_type", "")

        # Determine semantic kind (application-level span type)
        # Priority hierarchy for clear categorization
        semantic_kind = determine_semantic_kind(span_attributes)

        # Convert events to nested structure
        event_timestamps = []
        event_names = []
        event_attributes = []
        if span.events:
            for event in span.events:
                event_timestamps.append(self._nano_to_datetime(event.timestamp))
                event_names.append(event.name)
                event_attrs = {}
                if event.attributes:
                    event_attrs = {k: str(v) for k, v in event.attributes.items()}
                event_attributes.append(event_attrs)

        # Convert links to nested structure
        link_trace_ids = []
        link_span_ids = []
        link_attributes = []
        if span.links:
            for link in span.links:
                link_trace_ids.append(format(link.context.trace_id, "032x"))
                link_span_ids.append(format(link.context.span_id, "016x"))
                link_attrs = {}
                if link.attributes:
                    link_attrs = {k: str(v) for k, v in link.attributes.items()}
                link_attributes.append(link_attrs)

        return {
            # OTel Core (required)
            "Timestamp": timestamp,
            "TraceId": trace_id,
            "SpanId": span_id,
            "ParentSpanId": parent_span_id,
            "SpanName": span.name,
            "SpanKind": span_kind,
            "Duration": duration,
            "StatusCode": status_code,
            # OTel Optional (recommended)
            "StatusMessage": status_message,
            "SpanAttributes": span_attributes,
            "ResourceAttributes": resource_attrs,
            "Events.Timestamp": event_timestamps,
            "Events.Name": event_names,
            "Events.Attributes": event_attributes,
            "Links.TraceId": link_trace_ids,
            "Links.SpanId": link_span_ids,
            "Links.Attributes": link_attributes,
            # Custom Alphatrion fields
            "SemanticKind": semantic_kind,
            "ServiceName": service_name,
            "TeamId": team_id,
            "UserId": user_id,
            "RunId": run_id,
            "ExperimentId": experiment_id,
            "SessionId": session_id,
            "AgentId": agent_id,
            "AgentType": agent_type,
        }

    def _nano_to_datetime(self, nanoseconds: int) -> datetime:
        """Convert nanoseconds timestamp to datetime.

        Args:
            nanoseconds: Timestamp in nanoseconds

        Returns:
            datetime object
        """
        seconds = nanoseconds / 1_000_000_000
        return datetime.fromtimestamp(seconds, tz=UTC)

    def shutdown(self) -> None:
        """Shutdown the exporter and close ClickHouse connection."""
        try:
            self.trace_store.close()
        except Exception as e:
            logger.error(f"Failed to shutdown exporter: {e}")

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush any buffered spans.

        Args:
            timeout_millis: Timeout in milliseconds

        Returns:
            True if successful, False otherwise
        """
        # No buffering in this implementation
        return True


def determine_semantic_kind(
    attributes: dict[str, str], content_blocks: list[dict] = None
) -> str:
    """Determine the semantic kind of a span.

    Priority order:
    1. Content type based (thinking, llm, tool) - if content_blocks provided
    2. Tool calls (has tool attributes)
    3. LLM calls (has token usage)
    4. Database operations (has db attributes)
    5. HTTP requests (has http attributes)
    6. Traceloop semantic kinds (workflow, task, agent)
    7. Unknown

    Args:
        attributes: Span attributes
        content_blocks: Optional list of content blocks (for Claude agents)

    Returns:
        Semantic kind string
    """
    # Check content type first (Claude agents)
    if content_blocks:
        content_types = [b.get("type") for b in content_blocks if isinstance(b, dict)]
        if "tool_use" in content_types:
            return "tool"
        elif "thinking" in content_types:
            return "thinking"
        elif "text" in content_types:
            return "text-generation"
        # Has content blocks but unknown type - fallback to llm
        elif content_types:
            return "llm"

    # Check for tool calls (fallback)
    if "tool.name" in attributes:
        return "tool"

    # Check for LLM calls (fallback)
    if (
        "llm.usage.total_tokens" in attributes
        or "gen_ai.usage.output_tokens" in attributes
    ):
        return "llm"

    # Check for Traceloop semantic kinds
    if "traceloop.span.kind" in attributes:
        traceloop_kind = attributes["traceloop.span.kind"]
        if traceloop_kind in ("workflow", "task", "agent"):
            return traceloop_kind

    # Check for database operations
    if "db.system" in attributes or "db.statement" in attributes:
        return "database"

    # Check for HTTP requests
    if "http.method" in attributes or "http.url" in attributes:
        return "http"

    # Default to unknown
    return "unknown"
