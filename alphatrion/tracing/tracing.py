import inspect
import logging
import os
import uuid
from functools import wraps

from opentelemetry import trace
from opentelemetry.semconv_ai import TraceloopSpanKindValues
from traceloop.sdk.decorators import task as _task
from traceloop.sdk.decorators import workflow as _workflow

from alphatrion import envs
from alphatrion.runtime.contextvars import current_run_id, current_exp_id

logger = logging.getLogger(__name__)


def _set_span_attributes(run_id: uuid.UUID) -> None:
    """Helper to set span attributes for ClickHouse storage."""
    if os.getenv(envs.ENABLE_TRACING, "false").lower() != "true":
        return

    try:
        from alphatrion.runtime.runtime import global_runtime

        runtime = global_runtime()
        span = trace.get_current_span()
        if span.is_recording():
            span.set_attribute("run_id", str(run_id))
            span.set_attribute("project_id", str(runtime.current_proj.id))
            span.set_attribute("team_id", str(runtime.team_id))
            span.set_attribute("experiment_id", str(current_exp_id.get()))
    except (RuntimeError, AttributeError) as e:
        logger.debug(f"Could not set span attributes: {e}")


def _create_tracing_wrapper(func, traceloop_decorator):
    """Create a wrapper that sets span attributes and applies traceloop decorator."""

    @wraps(func)
    async def async_inner(*args, **kwargs):
        _set_span_attributes(current_run_id.get())
        return await func(*args, **kwargs)

    @wraps(func)
    def sync_inner(*args, **kwargs):
        _set_span_attributes(current_run_id.get())
        return func(*args, **kwargs)

    inner = async_inner if inspect.iscoroutinefunction(func) else sync_inner
    return traceloop_decorator(inner)


def task(
    version: int | None = None,
    method_name: str | None = None,
    span_kind: TraceloopSpanKindValues | None = TraceloopSpanKindValues.TASK,
):
    """Task decorator that sets trace attributes for ClickHouse storage."""

    def decorator(func):
        traceloop_decorator = _task(
            version=version,
            method_name=method_name,
            tlp_span_kind=span_kind,
        )
        return _create_tracing_wrapper(func, traceloop_decorator)

    return decorator


# run_id should only used in testing because other IDs may not exist
# at the same time.
def workflow(
    run_id: uuid.UUID | None = None,
    version: int | None = None,
    method_name: str | None = None,
    span_kind: TraceloopSpanKindValues | None = TraceloopSpanKindValues.WORKFLOW,
):
    """Workflow decorator with default run_id from context var.

    :param run_id: The run ID to use for the workflow as the identify name.
                   If None, use the current run ID from context var.
    """

    def decorator(func):
        @wraps(func)
        async def async_inner(*args, **kwargs):
            actual_run_id = run_id or current_run_id.get()
            _set_span_attributes(actual_run_id)
            return await func(*args, **kwargs)

        @wraps(func)
        def sync_inner(*args, **kwargs):
            actual_run_id = run_id or current_run_id.get()
            _set_span_attributes(actual_run_id)
            return func(*args, **kwargs)

        inner = async_inner if inspect.iscoroutinefunction(func) else sync_inner

        traceloop_decorator = _workflow(
            version=version,
            method_name=method_name,
            tlp_span_kind=span_kind,
        )

        return traceloop_decorator(inner)

    return decorator
