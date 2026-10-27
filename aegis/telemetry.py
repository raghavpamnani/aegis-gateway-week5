import os
from contextlib import contextmanager

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


class Telemetry:
    def __init__(self):
        self.provider = TracerProvider(resource=Resource.create({"service.name": "aegis-gateway"}))
        self.langfuse = None
        self.export_enabled = bool(os.getenv("AEGIS_OTLP_ENDPOINT"))
        if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
            from langfuse import Langfuse

            self.langfuse = Langfuse(tracer_provider=self.provider, should_export_span=lambda _: True)
            self.export_enabled = True
        elif self.export_enabled:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            headers = dict(
                item.split("=", 1) for item in os.getenv("AEGIS_OTLP_HEADERS", "").split(",") if "=" in item
            )
            self.provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=os.environ["AEGIS_OTLP_ENDPOINT"], headers=headers, timeout=2),
                    max_queue_size=256,
                    max_export_batch_size=32,
                    schedule_delay_millis=1000,
                )
            )
        self.tracer = self.provider.get_tracer("aegis", "0.1.0")

    @contextmanager
    def span(self, name, **attributes):
        with self.tracer.start_as_current_span(name, attributes=attributes) as span:
            yield span

    def close(self):
        self.provider.shutdown()

    @staticmethod
    def trace_id(span):
        return format(span.get_span_context().trace_id, "032x")


def mark_error(span, message):
    span.set_status(trace.Status(trace.StatusCode.ERROR, message))
