import inspect
import uuid
from functools import wraps

from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.semconv_ai import TraceloopSpanKindValues
from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import task as _task
from traceloop.sdk.decorators import workflow as _workflow

from alphatrion.run.run import current_run_id

Traceloop.init(
    app_name="alphatrion",
    # TODO: make this configurable
    exporter=ConsoleSpanExporter(),
    disable_batch=True,
    telemetry_enabled=False,
)


def task(
    version: int | None = None,
    method_name: str | None = None,
    tlp_span_kind: TraceloopSpanKindValues | None = TraceloopSpanKindValues.TASK,
):
    return _task(
        version=version,
        method_name=method_name,
        tlp_span_kind=tlp_span_kind,
    )


def workflow(
    run_id: uuid.UUID | None = None,
    version: int | None = None,
    method_name: str | None = None,
    tlp_span_kind: TraceloopSpanKindValues | None = TraceloopSpanKindValues.WORKFLOW,
):
    """Workflow decorator with default run_id from context var.
    :param run_id: The run ID to use for the workflow as the identify name.
                   If None, use the current run ID from context var, only for tests.
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            actual_run_id = run_id or current_run_id.get()
            wrapped_func = _workflow(
                name=str(actual_run_id),
                version=version,
                method_name=method_name,
                tlp_span_kind=tlp_span_kind,
            )(func)
            return await wrapped_func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            actual_run_id = run_id or current_run_id.get()
            wrapped_func = _workflow(
                name=str(actual_run_id),
                version=version,
                method_name=method_name,
                tlp_span_kind=tlp_span_kind,
            )(func)
            return wrapped_func(*args, **kwargs)

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
