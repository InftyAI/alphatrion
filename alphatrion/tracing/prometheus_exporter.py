"""
Prometheus Span Exporter.

Exports OpenTelemetry span metrics to Prometheus push gateway.
"""

import logging
import socket
import uuid

from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanExporter, SpanExportResult
from prometheus_client import (
    CollectorRegistry,
    Counter,
    Histogram,
    pushadd_to_gateway,
)

logger = logging.getLogger(__name__)


class PrometheusExporter(SpanExporter):
    """
    Span exporter that exports metrics to Prometheus push gateway.
    """

    def __init__(
        self,
        pushgateway_url: str,
        job_name: str = "alphatrion",
        grouping_key: dict[str, str] | None = None,
    ):
        """
        Initialize the Prometheus exporter.

        Args:
            pushgateway_url: URL of the Prometheus push gateway
            job_name: Job name for the metrics in Prometheus
            grouping_key: Additional grouping labels
        """
        self.pushgateway_url = pushgateway_url
        self.job_name = job_name

        if grouping_key is None:
            try:
                hostname = socket.gethostname()
                instance_id = (
                    f"{hostname}-{uuid.uuid4().hex}" if hostname else uuid.uuid4().hex
                )
            except Exception:
                instance_id = uuid.uuid4().hex

            self.grouping_key = {"instance": instance_id}
        else:
            self.grouping_key = grouping_key

        self.registry = CollectorRegistry()
        self._init_metrics()

        logger.info(
            f"PrometheusExporter initialized: pushgateway={pushgateway_url}, job={job_name}"
        )

    def _init_metrics(self):
        """Initialize Prometheus metrics."""
        # Token metrics
        self.llm_tokens_total = Counter(
            "llm_tokens_total",
            "Total LLM tokens consumed",
            ["team_id", "experiment_id", "model", "token_type"],
            registry=self.registry,
        )

        self.llm_input_tokens_total = Counter(
            "llm_input_tokens_total",
            "Total LLM input tokens consumed",
            ["team_id", "experiment_id", "model"],
            registry=self.registry,
        )

        self.llm_output_tokens_total = Counter(
            "llm_output_tokens_total",
            "Total LLM output tokens consumed",
            ["team_id", "experiment_id", "model"],
            registry=self.registry,
        )

        self.llm_cache_read_input_tokens_total = Counter(
            "llm_cache_read_input_tokens_total",
            "Total LLM cache read input tokens",
            ["team_id", "experiment_id", "model"],
            registry=self.registry,
        )

        self.llm_cache_creation_input_tokens_total = Counter(
            "llm_cache_creation_input_tokens_total",
            "Total LLM cache creation input tokens",
            ["team_id", "experiment_id", "model"],
            registry=self.registry,
        )

        # Cost metrics
        self.llm_cost_total = Counter(
            "llm_cost_total",
            "Total LLM cost in USD",
            ["team_id", "experiment_id", "model", "cost_type"],
            registry=self.registry,
        )

        self.llm_input_cost_total = Counter(
            "llm_input_cost_total",
            "Total LLM input cost in USD",
            ["team_id", "experiment_id", "model"],
            registry=self.registry,
        )

        self.llm_output_cost_total = Counter(
            "llm_output_cost_total",
            "Total LLM output cost in USD",
            ["team_id", "experiment_id", "model"],
            registry=self.registry,
        )

        self.llm_cache_read_cost_total = Counter(
            "llm_cache_read_cost_total",
            "Total LLM cache read cost in USD",
            ["team_id", "experiment_id", "model"],
            registry=self.registry,
        )

        self.llm_cache_creation_cost_total = Counter(
            "llm_cache_creation_cost_total",
            "Total LLM cache creation cost in USD",
            ["team_id", "experiment_id", "model"],
            registry=self.registry,
        )

        # Request metrics
        self.llm_requests_total = Counter(
            "llm_requests_total",
            "Total number of LLM requests",
            ["team_id", "experiment_id", "model", "status"],
            registry=self.registry,
        )

        # Latency metrics
        self.llm_request_duration_seconds = Histogram(
            "llm_request_duration_seconds",
            "LLM request duration in seconds",
            ["team_id", "experiment_id", "model"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
            registry=self.registry,
        )

        # Error metrics
        self.llm_errors_total = Counter(
            "llm_errors_total",
            "Total LLM errors by type",
            ["error_type"],
            registry=self.registry,
        )

    def export(self, spans: list[ReadableSpan]) -> SpanExportResult:
        """
        Export spans to Prometheus push gateway.

        Args:
            spans: List of spans to export

        Returns:
            SpanExportResult indicating success or failure
        """
        try:
            for span in spans:
                self._process_span(span)

            self._push_metrics()
            return SpanExportResult.SUCCESS

        except Exception as e:
            logger.error(f"Failed to export spans to Prometheus: {e}", exc_info=True)
            return SpanExportResult.FAILURE

    def _process_span(self, span: ReadableSpan):
        """Process a single span and update metrics."""
        try:
            if not span.attributes or "traceloop.workflow.name" not in span.attributes:
                return

            attributes = {k: str(v) for k, v in span.attributes.items()}
            team_id = attributes.get("team_id", "unknown")
            experiment_id = attributes.get("experiment_id", "unknown")

            if "llm.usage.total_tokens" not in attributes:
                return

            duration = (span.end_time - span.start_time) / 1_000_000_000
            status_map = {0: "UNSET", 1: "OK", 2: "ERROR"}
            status = status_map.get(span.status.status_code.value, "UNSET")

            if status == "ERROR":
                error_type = self._classify_error(span, attributes)
                self.llm_errors_total.labels(error_type=error_type).inc()

            self._process_llm_span(
                span, attributes, team_id, experiment_id, duration, status
            )

        except Exception as e:
            logger.error(f"Failed to process span: {e}", exc_info=True)

    def _classify_error(self, span: ReadableSpan, attributes: dict[str, str]) -> str:
        """Classify error type from span."""
        status_msg = (span.status.description or "").lower()

        if "timeout" in status_msg or "timed out" in status_msg:
            return "timeout"
        elif "rate limit" in status_msg or "429" in status_msg:
            return "rate_limit"
        elif "auth" in status_msg or "401" in status_msg or "403" in status_msg:
            return "auth_error"
        elif "not found" in status_msg or "404" in status_msg:
            return "not_found"
        elif "invalid" in status_msg or "400" in status_msg:
            return "invalid_request"
        elif "connection" in status_msg or "network" in status_msg:
            return "connection_error"
        elif "500" in status_msg or "502" in status_msg or "503" in status_msg:
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
        model = attributes.get(
            "gen_ai.request.model", attributes.get("gen_ai.response.model", "unknown")
        )

        # Token metrics
        total_tokens = int(attributes.get("llm.usage.total_tokens", 0))
        input_tokens = int(attributes.get("gen_ai.usage.input_tokens", 0))
        output_tokens = int(attributes.get("gen_ai.usage.output_tokens", 0))
        cache_read_input_tokens = int(
            attributes.get("gen_ai.usage.cache_read_input_tokens", 0)
        )
        cache_creation_input_tokens = int(
            attributes.get("gen_ai.usage.cache_creation_input_tokens", 0)
        )

        if total_tokens > 0:
            self.llm_tokens_total.labels(
                team_id=team_id,
                experiment_id=experiment_id,
                model=model,
                token_type="total",
            ).inc(total_tokens)

        if input_tokens > 0:
            self.llm_input_tokens_total.labels(
                team_id=team_id, experiment_id=experiment_id, model=model
            ).inc(input_tokens)
            self.llm_tokens_total.labels(
                team_id=team_id,
                experiment_id=experiment_id,
                model=model,
                token_type="input",
            ).inc(input_tokens)

        if output_tokens > 0:
            self.llm_output_tokens_total.labels(
                team_id=team_id, experiment_id=experiment_id, model=model
            ).inc(output_tokens)
            self.llm_tokens_total.labels(
                team_id=team_id,
                experiment_id=experiment_id,
                model=model,
                token_type="output",
            ).inc(output_tokens)

        if cache_read_input_tokens > 0:
            self.llm_cache_read_input_tokens_total.labels(
                team_id=team_id, experiment_id=experiment_id, model=model
            ).inc(cache_read_input_tokens)
            self.llm_tokens_total.labels(
                team_id=team_id,
                experiment_id=experiment_id,
                model=model,
                token_type="cache_read_input",
            ).inc(cache_read_input_tokens)

        if cache_creation_input_tokens > 0:
            self.llm_cache_creation_input_tokens_total.labels(
                team_id=team_id, experiment_id=experiment_id, model=model
            ).inc(cache_creation_input_tokens)
            self.llm_tokens_total.labels(
                team_id=team_id,
                experiment_id=experiment_id,
                model=model,
                token_type="cache_creation_input",
            ).inc(cache_creation_input_tokens)

        # Cost metrics - read from enriched attributes
        try:
            total_cost = float(attributes.get("alphatrion.cost.total_tokens", 0))
            input_cost = float(attributes.get("alphatrion.cost.input_tokens", 0))
            output_cost = float(attributes.get("alphatrion.cost.output_tokens", 0))
            cache_read_cost = float(
                attributes.get("alphatrion.cost.cache_read_input_tokens", 0)
            )
            cache_creation_cost = float(
                attributes.get("alphatrion.cost.cache_creation_input_tokens", 0)
            )

            if total_cost > 0:
                self.llm_cost_total.labels(
                    team_id=team_id,
                    experiment_id=experiment_id,
                    model=model,
                    cost_type="total",
                ).inc(total_cost)

            if input_cost > 0:
                self.llm_input_cost_total.labels(
                    team_id=team_id, experiment_id=experiment_id, model=model
                ).inc(input_cost)

            if output_cost > 0:
                self.llm_output_cost_total.labels(
                    team_id=team_id, experiment_id=experiment_id, model=model
                ).inc(output_cost)

            if cache_read_cost > 0:
                self.llm_cache_read_cost_total.labels(
                    team_id=team_id, experiment_id=experiment_id, model=model
                ).inc(cache_read_cost)

            if cache_creation_cost > 0:
                self.llm_cache_creation_cost_total.labels(
                    team_id=team_id, experiment_id=experiment_id, model=model
                ).inc(cache_creation_cost)

        except (ValueError, TypeError) as e:
            logger.debug(f"No cost data available for span: {e}")

        # Request count
        self.llm_requests_total.labels(
            team_id=team_id, experiment_id=experiment_id, model=model, status=status
        ).inc()

        # Duration
        self.llm_request_duration_seconds.labels(
            team_id=team_id, experiment_id=experiment_id, model=model
        ).observe(duration)

    def _push_metrics(self):
        """Push metrics to Prometheus push gateway."""
        try:
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
        """Shutdown the exporter and perform final push."""
        try:
            self._push_metrics()
            logger.info("PrometheusExporter shut down successfully")
        except Exception as e:
            logger.error(f"Error during PrometheusExporter shutdown: {e}")

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Force flush metrics to push gateway."""
        try:
            self._push_metrics()
            return True
        except Exception as e:
            logger.error(f"Failed to force flush metrics: {e}")
            return False
