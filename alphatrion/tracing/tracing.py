from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.semconv_ai import TraceloopSpanKindValues
from traceloop.sdk import Traceloop
from traceloop.sdk.decorators import task as _task
from traceloop.sdk.decorators import workflow as _workflow

Traceloop.init(
    # TODO: make this configurable
    exporter=ConsoleSpanExporter(),
    disable_batch=True,
)


def task(
    name: str | None = None,
    version: int | None = None,
    method_name: str | None = None,
    tlp_span_kind: TraceloopSpanKindValues | None = TraceloopSpanKindValues.TASK,
):
    return _task(
        name=name,
        version=version,
        method_name=method_name,
        tlp_span_kind=tlp_span_kind,
    )


def workflow(
    name: str | None = None,
    version: int | None = None,
    method_name: str | None = None,
    tlp_span_kind: TraceloopSpanKindValues | None = TraceloopSpanKindValues.WORKFLOW,
):
    return _workflow(
        name=name,
        version=version,
        method_name=method_name,
        tlp_span_kind=tlp_span_kind,
    )
