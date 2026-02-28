import logging

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan, Span, SpanProcessor

from alphatrion.runtime.contextvars import current_exp_id, current_run_id

logger = logging.getLogger(__name__)


class ContextAttributesSpanProcessor(SpanProcessor):
    """
    SpanProcessor that adds run_id, team_id, experiment_id
    to all spans.
    """

    def on_start(self, span: Span, parent_context: Context | None = None) -> None:
        """Called when a span is started.

        Adds context attributes (run_id, team_id, experiment_id) to the
        span. This ensures all spans in the trace have these attributes, including
        child spans created by instrumented libraries (OpenAI, database drivers, etc.).

        Args:
            span: The span that was just started
            parent_context: The parent context (unused)
        """
        try:
            from alphatrion.runtime.runtime import global_runtime

            run_id = current_run_id.get(None)
            exp_id = current_exp_id.get(None)

            if run_id is None:
                # No run context, skip setting attributes
                return

            runtime = global_runtime()

            span.set_attribute("run_id", str(run_id))
            span.set_attribute("experiment_id", str(exp_id))
            span.set_attribute("team_id", str(runtime.team_id))
        except (RuntimeError, AttributeError) as e:
            logger.debug(f"Could not set span attributes in processor: {e}")

    def on_end(self, span: ReadableSpan) -> None:
        """Called when a span is ended (no-op)."""
        pass

    def shutdown(self) -> None:
        """Called when the processor is shut down (no-op)."""
        pass

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """Called to force flush (no-op, always returns True)."""
        return True
