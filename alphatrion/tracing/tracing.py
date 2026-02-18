import uuid

from opentelemetry.semconv_ai import TraceloopSpanKindValues
from traceloop.sdk.decorators import task as _task
from traceloop.sdk.decorators import workflow as _workflow


def task(
    version: int | None = None,
    method_name: str | None = None,
    span_kind: TraceloopSpanKindValues | None = TraceloopSpanKindValues.TASK,
):
    """Task decorator for tracing.

    Attributes (run_id, project_id, team_id, experiment_id) are automatically
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
    run_id: uuid.UUID | None = None,
    version: int | None = None,
    method_name: str | None = None,
    span_kind: TraceloopSpanKindValues | None = TraceloopSpanKindValues.WORKFLOW,
):
    """Workflow decorator for tracing.

    Attributes (run_id, project_id, team_id, experiment_id) are automatically
    added to all spans by ContextAttributesSpanProcessor.

    :param run_id: The run ID (unused, kept for compatibility)
    """

    def decorator(func):
        return _workflow(
            name=str(run_id) if run_id else None,
            version=version,
            method_name=method_name,
            tlp_span_kind=span_kind,
        )(func)

    return decorator
