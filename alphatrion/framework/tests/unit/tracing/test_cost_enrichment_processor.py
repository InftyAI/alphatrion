from types import SimpleNamespace
from unittest import mock

from alphatrion.framework.tracing.cost_enrichment_processor import (
    CostEnrichmentProcessor,
)

COSTS = {
    "input_cost": 0.0,
    "output_cost": 0.0,
    "cache_creation_input_cost": 0.0,
    "cache_read_input_cost": 0.0,
}


def make_span(**usage):
    attributes = {f"gen_ai.usage.{k}": v for k, v in usage.items()}
    attributes["gen_ai.request.model"] = "test-model"
    return SimpleNamespace(attributes=attributes, _attributes=attributes)


def enrich(span):
    with mock.patch(
        "alphatrion.framework.tracing.cost_enrichment_processor.calculate_cost",
        return_value=COSTS,
    ) as calculate_cost:
        CostEnrichmentProcessor().on_end(span)
    return calculate_cost.call_args.kwargs


def test_cached_tokens_are_not_charged_as_regular_input():
    # gen_ai.usage.input_tokens includes cached tokens.
    kwargs = enrich(
        make_span(
            input_tokens=100,
            output_tokens=10,
            cache_read_input_tokens=30,
            cache_creation_input_tokens=20,
        )
    )

    assert kwargs["input_tokens"] == 50
    assert kwargs["cache_read_input_tokens"] == 30
    assert kwargs["cache_creation_input_tokens"] == 20


def test_input_tokens_without_cache():
    kwargs = enrich(make_span(input_tokens=100, output_tokens=10))

    assert kwargs["input_tokens"] == 100


def test_regular_input_tokens_never_negative():
    kwargs = enrich(make_span(input_tokens=10, cache_read_input_tokens=30))

    assert kwargs["input_tokens"] == 0
