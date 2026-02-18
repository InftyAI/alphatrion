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
from alphatrion.run.run import current_run_id
from alphatrion.experiment.base import current_exp_id

logger = logging.getLogger(__name__)

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
    span_kind: TraceloopSpanKindValues | None = TraceloopSpanKindValues.WORKFLOW,
):
    """Workflow decorator with default run_id from context var.
    :param run_id: The run ID to use for the workflow as the identify name.
                   If None, use the current run ID from context var, only for tests.
    """

    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            actual_run_id = run_id or current_run_id.get()

            # Create an inner wrapper that sets span attributes
            @wraps(func)
            async def inner_wrapper(*inner_args, **inner_kwargs):
                # Set span attributes within the workflow span context
                if os.getenv(envs.ENABLE_TRACING, "false").lower() == "true":
                    try:
                        from alphatrion.runtime.runtime import global_runtime

                        runtime = global_runtime()
                        span = trace.get_current_span()
                        if span.is_recording():
                            span.set_attribute("run_id", str(actual_run_id))
                            span.set_attribute(
                                "project_id", str(runtime.current_proj.id)
                            )
                            span.set_attribute("team_id", str(runtime.team_id))
                            span.set_attribute("experiment_id", str(current_exp_id.get()))
                    except (RuntimeError, AttributeError) as e:
                        logger.debug(f"Could not set span attributes: {e}")

                # Call the original function
                return await func(*inner_args, **inner_kwargs)

            # Wrap the inner function with traceloop workflow decorator
            wrapped_func = _workflow(
                name=str(actual_run_id),
                version=version,
                method_name=method_name,
                tlp_span_kind=span_kind,
            )(inner_wrapper)

            # Execute the wrapped function
            return await wrapped_func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            actual_run_id = run_id or current_run_id.get()

            # Create an inner wrapper that sets span attributes
            @wraps(func)
            def inner_wrapper(*inner_args, **inner_kwargs):
                # Set span attributes within the workflow span context
                if os.getenv(envs.ENABLE_TRACING, "false").lower() == "true":
                    try:
                        from alphatrion.runtime.runtime import global_runtime

                        runtime = global_runtime()
                        span = trace.get_current_span()
                        if span.is_recording():
                            span.set_attribute("run_id", str(actual_run_id))
                            span.set_attribute(
                                "project_id", str(runtime.current_proj.id)
                            )
                            span.set_attribute("team_id", str(runtime.team_id))
                            span.set_attribute("experiment_id", str(current_exp_id.get()))
                    except (RuntimeError, AttributeError) as e:
                        logger.debug(f"Could not set span attributes: {e}")

                # Call the original function
                return func(*inner_args, **inner_kwargs)

            # Wrap the inner function with traceloop workflow decorator
            wrapped_func = _workflow(
                name=str(actual_run_id),
                version=version,
                method_name=method_name,
                tlp_span_kind=span_kind,
            )(inner_wrapper)

            # Execute the wrapped function
            return wrapped_func(*args, **kwargs)

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
