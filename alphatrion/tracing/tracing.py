
from opentelemetry.semconv_ai import TraceloopSpanKindValues
from traceloop.sdk.decorators import agent as _agent
from traceloop.sdk.decorators import task as _task
from traceloop.sdk.decorators import tool as _tool
from traceloop.sdk.decorators import workflow as _workflow


def task(
    version: int | None = None,
    method_name: str | None = None,
    span_kind: TraceloopSpanKindValues | None = TraceloopSpanKindValues.TASK,
):
    """Task decorator for tracing.

    Attributes (run_id, team_id, experiment_id) are automatically
    added to all spans by ContextAttributesSpanProcessor.
    """

    def decorator(func):
        return _task(
            version=version,
            method_name=method_name,
            tlp_span_kind=span_kind,
        )(func)

    return decorator


def workflow(
    name: str | None = None,
    version: int | None = None,
    method_name: str | None = None,
    span_kind: TraceloopSpanKindValues | None = TraceloopSpanKindValues.WORKFLOW,
):
    """Workflow decorator for tracing.

    Attributes (run_id, team_id, experiment_id) are automatically
    added to all spans by ContextAttributesSpanProcessor.

    :param name: The workflow name (optional)
    """

    def decorator(func):
        return _workflow(
            name=name,
            version=version,
            method_name=method_name,
            tlp_span_kind=span_kind,
        )(func)

    return decorator


def tool(
    version: int | None = None,
    method_name: str | None = None,
):
    """Tool decorator for tracing.

    Attributes (run_id, team_id, experiment_id) are automatically
    added to all spans by ContextAttributesSpanProcessor.
    """

    def decorator(func):
        return _tool(
            version=version,
            method_name=method_name,
        )(func)

    return decorator


def agent(
    version: int | None = None,
    method_name: str | None = None,
):
    """Agent decorator for tracing.

    Attributes (run_id, team_id, experiment_id) are automatically
    added to all spans by ContextAttributesSpanProcessor.
    """

    def decorator(func):
        return _agent(
            version=version,
            method_name=method_name,
        )(func)

    return decorator
