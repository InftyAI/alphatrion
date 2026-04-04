"""
Cost Enrichment Span Processor.

This processor enriches spans with cost information by calculating costs from token usage.
It runs early in the processing chain so that downstream processors and exporters can
access pre-calculated costs from span attributes.
"""

import logging

from opentelemetry.context import Context
from opentelemetry.sdk.trace import ReadableSpan
from opentelemetry.sdk.trace.export import SpanProcessor

from alphatrion.utils.pricing import calculate_cost

logger = logging.getLogger(__name__)


class CostEnrichmentProcessor(SpanProcessor):
    """
    Span processor that enriches spans with cost information.

    This processor checks if cost attributes are already present in a span.
    If not, it calculates costs from token usage and adds them to the span's
    attributes dictionary. This ensures all downstream processors and exporters
    have access to consistent cost data.
    """

    def on_start(self, span: ReadableSpan, parent_context: Context | None = None):
        """Called when a span is started. No-op for this processor."""
        pass

    def on_end(self, span: ReadableSpan):
        """
        Called when a span ends. Calculate and add cost attributes if missing.

        Args:
            span: The completed span
        """
        try:
            # Only process spans with attributes
            if not span.attributes:
                return

            # Check if costs are already present
            if "alphatrion.cost.total_tokens" in span.attributes:
                # Costs already calculated (e.g., in claude.py)
                return

            # Check if this is an LLM span with token usage
            if "gen_ai.usage.input_tokens" not in span.attributes:
                # Not an LLM span, skip
                return

            # Extract token usage
            attributes = span.attributes
            provider = determine_provider(str(attributes.get("gen_ai.openai.api_base")))
            model = str(
                attributes.get("gen_ai.request.model")
                or attributes.get("gen_ai.response.model", "")
            )
            input_tokens = int(attributes.get("gen_ai.usage.input_tokens", 0))
            output_tokens = int(attributes.get("gen_ai.usage.output_tokens", 0))
            cache_creation_input_tokens = int(
                attributes.get("gen_ai.usage.cache_creation_input_tokens", 0)
            )
            cache_read_input_tokens = int(
                attributes.get("gen_ai.usage.cache_read_input_tokens", 0)
            )

            # Calculate costs
            cost_result = calculate_cost(
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_input_tokens=cache_creation_input_tokens,
                cache_read_input_tokens=cache_read_input_tokens,
            )

            # Add cost attributes to span
            # Note: We can't modify ReadableSpan.attributes directly after span ends,
            # but we can modify the underlying _attributes dict that will be read
            # by exporters. This is a bit of a hack but it's the only way to enrich
            # spans post-creation without modifying OpenTelemetry internals.
            if hasattr(span, "_attributes"):
                span._attributes["alphatrion.cost.total_tokens"] = str(
                    cost_result["total_cost"]
                )
                span._attributes["alphatrion.cost.input_tokens"] = str(
                    cost_result["input_cost"]
                )
                span._attributes["alphatrion.cost.output_tokens"] = str(
                    cost_result["output_cost"]
                )
                span._attributes["alphatrion.cost.cache_creation_input_tokens"] = str(
                    cost_result["cache_creation_input_cost"]
                )
                span._attributes["alphatrion.cost.cache_read_input_tokens"] = str(
                    cost_result["cache_read_input_cost"]
                )
                logger.debug(
                    f"Enriched span {span.name} with cost: ${cost_result['total_cost']:.6f}"
                )

        except Exception as e:
            logger.warning(f"Failed to enrich span with cost: {e}", exc_info=True)

    def shutdown(self):
        """Shutdown the processor."""
        logger.info("CostEnrichmentProcessor shut down successfully")

    def force_flush(self, timeout_millis: int = 30000) -> bool:
        """
        Force flush (no-op for this processor).

        Args:
            timeout_millis: Timeout in milliseconds

        Returns:
            True always
        """
        return True


def determine_provider(api_base: str) -> str:
    """Determine provider from API base URL.

    Args:
        api_base: API base URL (e.g., "https://api.anthropic.com")

    Returns:
        Provider name (e.g., "anthropic", "openai", "deepinfra", or "unknown")
    """
    api_base = api_base.lower()
    if "anthropic" in api_base:
        return "anthropic"
    elif "deepinfra" in api_base:
        return "deepinfra"
    elif "openai" in api_base:
        return "openai"
    else:
        return "unknown"
