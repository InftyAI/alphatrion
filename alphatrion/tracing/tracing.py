import uuid
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.semconv_ai import TraceloopSpanKindValues
from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import task as _task
from traceloop.sdk.decorators import workflow as _workflow

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
    run_id: uuid.UUID,
    version: int | None = None,
    method_name: str | None = None,
    tlp_span_kind: TraceloopSpanKindValues | None = TraceloopSpanKindValues.WORKFLOW,
):
    return _workflow(
        name=str(run_id),
        version=version,
        method_name=method_name,
        tlp_span_kind=tlp_span_kind,
    )
