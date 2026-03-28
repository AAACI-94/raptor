"""OpenTelemetry setup following GenAI Semantic Conventions.

When OTEL_EXPORTER_OTLP_ENDPOINT is empty, uses no-op providers (no background threads).
"""

import logging
from contextlib import contextmanager
from typing import Any, Generator

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource

from app.core.config import settings

logger = logging.getLogger(__name__)

_tracer: trace.Tracer | None = None
_meter: metrics.Meter | None = None


def init_telemetry() -> None:
    """Initialize OpenTelemetry. Skips exporters if no endpoint configured."""
    global _tracer, _meter

    endpoint = settings.otel_exporter_otlp_endpoint

    if not endpoint:
        # No-op: create tracers without exporters (no background threads)
        _tracer = trace.get_tracer("raptor", settings.version)
        _meter = metrics.get_meter("raptor", settings.version)
        logger.info("[telemetry] No OTLP endpoint, using no-op providers")
        return

    resource = Resource.create({
        "service.name": settings.otel_service_name,
        "service.version": settings.version,
    })

    # Traces (with exporter)
    try:
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

        trace_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        trace_provider = TracerProvider(resource=resource)
        trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
        trace.set_tracer_provider(trace_provider)
        _tracer = trace.get_tracer("raptor", settings.version)
        logger.info("[telemetry] Trace provider initialized, exporting to %s", endpoint)
    except Exception as e:
        logger.warning("[telemetry] Failed to initialize trace exporter: %s", e)
        _tracer = trace.get_tracer("raptor", settings.version)

    # Metrics (with exporter)
    try:
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

        metric_exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True)
        metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=30000)
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)
        _meter = metrics.get_meter("raptor", settings.version)
        logger.info("[telemetry] Metric provider initialized")
    except Exception as e:
        logger.warning("[telemetry] Failed to initialize metric exporter: %s", e)
        _meter = metrics.get_meter("raptor", settings.version)


def get_tracer() -> trace.Tracer:
    """Get the application tracer."""
    global _tracer
    if _tracer is None:
        _tracer = trace.get_tracer("raptor")
    return _tracer


def get_meter() -> metrics.Meter:
    """Get the application meter."""
    global _meter
    if _meter is None:
        _meter = metrics.get_meter("raptor")
    return _meter


@contextmanager
def agent_span(
    agent_role: str,
    operation: str,
    project_id: str | None = None,
    artifact_type: str | None = None,
    **extra_attrs: Any,
) -> Generator[trace.Span, None, None]:
    """Create an instrumented span for an agent operation."""
    tracer = get_tracer()
    attrs: dict[str, Any] = {
        "raptor.agent": agent_role,
        "raptor.operation": operation,
    }
    if project_id:
        attrs["raptor.project_id"] = project_id
    if artifact_type:
        attrs["raptor.artifact_type"] = artifact_type
    attrs.update(extra_attrs)

    with tracer.start_as_current_span(f"{agent_role}.{operation}", attributes=attrs) as span:
        yield span


def record_llm_call(
    span: trace.Span,
    model: str,
    input_tokens: int,
    output_tokens: int,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    finish_reason: str = "end_turn",
    cache_read_tokens: int = 0,
    cache_write_tokens: int = 0,
) -> None:
    """Record GenAI semantic convention attributes on a span."""
    span.set_attribute("gen_ai.system", "anthropic")
    span.set_attribute("gen_ai.request.model", model)
    span.set_attribute("gen_ai.request.max_tokens", max_tokens)
    span.set_attribute("gen_ai.request.temperature", temperature)
    span.set_attribute("gen_ai.response.model", model)
    span.set_attribute("gen_ai.usage.input_tokens", input_tokens)
    span.set_attribute("gen_ai.usage.output_tokens", output_tokens)
    span.set_attribute("gen_ai.response.finish_reasons", [finish_reason])

    if cache_read_tokens:
        span.set_attribute("gen_ai.usage.cache_read_tokens", cache_read_tokens)
    if cache_write_tokens:
        span.set_attribute("gen_ai.usage.cache_write_tokens", cache_write_tokens)


def record_decision(
    span: trace.Span,
    agent: str,
    decision: str,
    rationale: str,
    confidence: float,
    alternatives: list[str] | None = None,
) -> None:
    """Record an agent decision as an OTel event."""
    import json
    attrs: dict[str, Any] = {
        "raptor.decision": decision,
        "raptor.rationale": rationale,
        "raptor.confidence": confidence,
        "raptor.agent": agent,
    }
    if alternatives:
        attrs["raptor.alternatives"] = json.dumps(alternatives)
    span.add_event("agent_decision", attributes=attrs)
