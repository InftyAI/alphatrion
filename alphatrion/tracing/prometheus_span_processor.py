# ruff: noqa: PLR0911

import logging
import socket
import uuid

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanProcessor
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    pushadd_to_gateway,
)

logger = logging.getLogger(__name__)


class PrometheusSpanProcessor(SpanProcessor):
    """
    Span processor that exports OpenTelemetry span metrics to Prometheus push gateway.

    This processor extracts metrics from LLM spans (tokens, latency, etc.) and pushes
    them to a Prometheus push gateway, making them available for scraping by Prometheus.
    """

    def __init__(
        self,
        pushgateway_url: str,
        job_name: str = "alphatrion",
        grouping_key: dict[str, str] | None = None,
    ):
        """
        Initialize the Prometheus span processor.

        Args:
            pushgateway_url: URL of the Prometheus push gateway (e.g., "localhost:9091")
            job_name: Job name for the metrics in Prometheus
            grouping_key: Additional grouping labels (e.g., {"instance": "app-1"})
        """
        self.pushgateway_url = pushgateway_url
        self.job_name = job_name

        # Generate unique instance identifier to prevent metrics from being overwritten
        # Combines hostname (for traceability) with UUID (for uniqueness)
        if grouping_key is None:
            try:
                hostname = socket.gethostname()
                if hostname:
                    instance_id = f"{hostname}-{uuid.uuid4().hex}"
                else:
                    instance_id = uuid.uuid4().hex
            except Exception:
                instance_id = uuid.uuid4().hex

            self.grouping_key = {"instance": instance_id}
        else:
            self.grouping_key = grouping_key

        # Create a separate registry for push gateway metrics
        self.registry = CollectorRegistry()

        # Define metrics
        self._init_metrics()

        logger.info(
            f"PrometheusSpanProcessor initialized: pushgateway={pushgateway_url}, "
            f"job={job_name}"
        )

    def _init_metrics(self):
        """Initialize Prometheus metrics."""

        # LLM Token usage metrics
        self.llm_tokens_total = Counter(
            "alphatrion_llm_tokens_total",
            "Total LLM tokens consumed",
            ["team_id", "experiment_id", "model", "token_type"],
            registry=self.registry,
        )

        self.llm_input_tokens_total = Counter(
            "alphatrion_llm_input_tokens_total",
            "Total LLM input tokens consumed",
            ["team_id", "experiment_id", "model"],
            registry=self.registry,
        )

        self.llm_output_tokens_total = Counter(
            "alphatrion_llm_output_tokens_total",
            "Total LLM output tokens consumed",
            ["team_id", "experiment_id", "model"],
            registry=self.registry,
        )

        # LLM Request metrics
        self.llm_requests_total = Counter(
            "alphatrion_llm_requests_total",
            "Total number of LLM requests",
            ["team_id", "experiment_id", "model", "status"],
            registry=self.registry,
        )

        # LLM Latency metrics
        self.llm_duration_seconds = Histogram(
            "alphatrion_llm_duration_seconds",
            "LLM request duration in seconds",
            ["team_id", "experiment_id", "model"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry,
        )

        # Error tracking
        self.llm_errors_total = Counter(
            "alphatrion_llm_errors_total",
            "Total LLM errors by type",
            ["error_type"],
            registry=self.registry,
        )

    def on_start(self, span: ReadableSpan, parent_context: Context | None = None):
        """Called when a span is started. No-op for this processor."""
        pass

    def on_end(self, span: ReadableSpan):
        """
        Called when a span ends. Extract metrics and push to Prometheus.

        Args:
            span: The completed span
        """
        try:
            # Only process spans with traceloop attributes
            # (same filter as ClickHouse exporter)
            if not span.attributes or "traceloop.workflow.name" not in span.attributes:
                return

            # Extract common attributes
            attributes = {k: str(v) for k, v in span.attributes.items()}
            team_id = attributes.get("team_id", "unknown")
            experiment_id = attributes.get("experiment_id", "unknown")

            # Only process LLM spans
            if "llm.usage.total_tokens" not in attributes:
                return

            # Calculate duration in seconds
            duration = (span.end_time - span.start_time) / 1_000_000_000

            # Status
            status_map = {0: "UNSET", 1: "OK", 2: "ERROR"}
            status = status_map.get(span.status.status_code.value, "UNSET")

            # Track errors
            if status == "ERROR":
                error_type = self._classify_error(span, attributes)
                self.llm_errors_total.labels(
                    error_type=error_type,
                ).inc()

            # Process LLM-specific metrics
            self._process_llm_span(
                span, attributes, team_id, experiment_id, duration, status
            )

            # Push to gateway
            self._push_metrics()

        except Exception as e:
            logger.error(f"Failed to process span metrics: {e}", exc_info=True)

    def _classify_error(self, span: ReadableSpan, attributes: dict[str, str]) -> str:
        """
        Classify error type from span.

        Args:
            span: The span with error
            attributes: Span attributes

        Returns:
            Error type string
        """
        # Check status message for common error patterns
        status_msg = span.status.description or ""
        status_msg_lower = status_msg.lower()

        # Common error patterns
        if "timeout" in status_msg_lower or "timed out" in status_msg_lower:
            return "timeout"
        elif "rate limit" in status_msg_lower or "429" in status_msg_lower:
            return "rate_limit"
        elif (
            "auth" in status_msg_lower
            or "401" in status_msg_lower
            or "403" in status_msg_lower
        ):
            return "auth_error"
        elif "not found" in status_msg_lower or "404" in status_msg_lower:
            return "not_found"
        elif "invalid" in status_msg_lower or "400" in status_msg_lower:
            return "invalid_request"
        elif "connection" in status_msg_lower or "network" in status_msg_lower:
            return "connection_error"
        elif (
            "500" in status_msg_lower
            or "502" in status_msg_lower
            or "503" in status_msg_lower
        ):
            return "server_error"
        else:
            return "unknown"

    def _process_llm_span(
        self,
        span: ReadableSpan,
        attributes: dict[str, str],
        team_id: str,
        experiment_id: str,
        duration: float,
        status: str,
    ):
        """Process LLM-specific metrics from a span."""
        # Extract model name
        model = attributes.get(
            "gen_ai.request.model", attributes.get("gen_ai.response.model", "unknown")
        )

        # Token metrics
        total_tokens = int(attributes.get("llm.usage.total_tokens", 0))
        input_tokens = int(attributes.get("gen_ai.usage.input_tokens", 0))
        output_tokens = int(attributes.get("gen_ai.usage.output_tokens", 0))

        if total_tokens > 0:
            self.llm_tokens_total.labels(
                team_id=team_id,
                experiment_id=experiment_id,
                model=model,
                token_type="total",
            ).inc(total_tokens)

        if input_tokens > 0:
            self.llm_input_tokens_total.labels(
                team_id=team_id,
                experiment_id=experiment_id,
                model=model,
            ).inc(input_tokens)

            self.llm_tokens_total.labels(
                team_id=team_id,
                experiment_id=experiment_id,
                model=model,
                token_type="input",
            ).inc(input_tokens)

        if output_tokens > 0:
            self.llm_output_tokens_total.labels(
                team_id=team_id,
                experiment_id=experiment_id,
                model=model,
            ).inc(output_tokens)

            self.llm_tokens_total.labels(
                team_id=team_id,
                experiment_id=experiment_id,
                model=model,
                token_type="output",
            ).inc(output_tokens)

        # Request count
        self.llm_requests_total.labels(
            team_id=team_id,
            experiment_id=experiment_id,
            model=model,
            status=status,
        ).inc()

        # Duration
        self.llm_duration_seconds.labels(
            team_id=team_id,
            experiment_id=experiment_id,
            model=model,
        ).observe(duration)

    def _push_metrics(self):
        """Push metrics to Prometheus push gateway."""
        try:
            # Use pushadd_to_gateway to accumulate counters instead of replacing them
            pushadd_to_gateway(
                self.pushgateway_url,
                job=self.job_name,
                registry=self.registry,
                grouping_key=self.grouping_key,
            )
            logger.debug("Successfully pushed metrics to Prometheus push gateway")
        except Exception as e:
            logger.warning(f"Failed to push metrics to Prometheus: {e}")

    def shutdown(self):
        """Shutdown the processor and perform final push."""
        try:
            self._push_metrics()
            logger.info("PrometheusSpanProcessor shut down successfully")
        except Exception as e:
            logger.error(f"Error during PrometheusSpanProcessor shutdown: {e}")

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """
        Force flush metrics to push gateway.

        Args:
            timeout_millis: Timeout in milliseconds (not used)

        Returns:
            True if successful, False otherwise
        """
        try:
            self._push_metrics()
            return True
        except Exception as e:
            logger.error(f"Failed to force flush metrics: {e}")
            return False
