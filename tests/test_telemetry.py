from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from aegis.telemetry import Telemetry


def test_official_langfuse_sdk_exports_nested_spans(monkeypatch):
    import langfuse

    real_client = langfuse.Langfuse
    capture = InMemorySpanExporter()
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-aegis-test-only")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-aegis-test-only")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "http://localhost:3000")
    monkeypatch.setattr(langfuse, "Langfuse", lambda **kw: real_client(span_exporter=capture, **kw))
    telemetry = Telemetry()
    with telemetry.span("investigation", **{"aegis.request_id": "test-run"}) as root:
        root_id = root.get_span_context().span_id
        with telemetry.span("model.attempt"):
            pass
    telemetry.provider.force_flush()
    spans = capture.get_finished_spans()
    assert {s.name for s in spans} == {"investigation", "model.attempt"}
    child = next(s for s in spans if s.name == "model.attempt")
    assert child.parent.span_id == root_id
    assert telemetry.export_enabled
    telemetry.close()
