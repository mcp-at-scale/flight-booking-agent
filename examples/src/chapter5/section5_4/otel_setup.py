"""OpenTelemetry setup for Chapter 5 §5.4.

Configures the global tracer and meter providers with an OTLP exporter,
the W3C Trace Context propagator (so SEP-414's _meta keys interop with
upstream and downstream OTEL services), and a head-based sampler.

Call ``setup_otel`` once at process startup before importing the
@otel_trace_tool decorator from this module's ``tracing.py`` counterpart.
The decorator reads tracer + meter handles via OTEL's global lookup,
so configuration done here is all the per-tool wrapper needs.

Environment variables consulted (the OTEL Python SDK reads many more;
these are the ones the chapter §5.4 examples document):

- OTEL_EXPORTER_OTLP_ENDPOINT: gRPC OTLP endpoint, e.g.
  ``http://localhost:4317`` (Jaeger, Tempo, OTEL collector, etc.)
- OTEL_SERVICE_NAME: service.resource attribute; defaults to
  ``flight-booking-mcp-server``
- OTEL_TRACES_SAMPLER_ARG: head-based sample ratio (0.0-1.0);
  defaults to 1.0 for the chapter demo; production deployments should
  set this to 0.01-0.1 and use tail-based sampling at the collector
"""

from __future__ import annotations

import os
import time

from opentelemetry import metrics, propagate, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.propagators.composite import CompositePropagator
from opentelemetry.propagators.textmap import DefaultGetter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import ParentBasedTraceIdRatio
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from opentelemetry.baggage.propagation import W3CBaggagePropagator


# Histogram bucket boundaries from the OpenTelemetry semantic conventions
# for MCP. Same boundaries for every operation-duration metric so dashboards
# render consistently across the fleet.
MCP_DURATION_BUCKETS = [0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1, 2, 5, 10, 30, 60, 120, 300]


def setup_otel() -> None:
    """Configure global tracer + meter providers + W3C propagators.

    Idempotent; safe to call multiple times.
    """
    service_name = os.environ.get("OTEL_SERVICE_NAME", "flight-booking-mcp-server")
    resource = Resource.create(attributes={"service.name": service_name})

    # Tracer
    tracer_provider = TracerProvider(
        resource=resource,
        sampler=_make_sampler(),
    )
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter())
    )
    trace.set_tracer_provider(tracer_provider)

    # Meter
    meter_reader = PeriodicExportingMetricReader(OTLPMetricExporter())
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[meter_reader],
    )
    metrics.set_meter_provider(meter_provider)

    # W3C Trace Context + Baggage propagators so SEP-414's _meta keys
    # interoperate with upstream hosts and downstream services that
    # speak standard OTEL propagation.
    propagate.set_global_textmap(
        CompositePropagator([
            TraceContextTextMapPropagator(),
            W3CBaggagePropagator(),
        ])
    )


def _make_sampler() -> ParentBasedTraceIdRatio:
    """Head-based sampler honoring the parent trace's sampling decision.

    Use OTEL_TRACES_SAMPLER_ARG to control the ratio for traces that
    don't have an upstream decision; defaults to 1.0 (record everything)
    for the chapter demo. Production should pair a low head ratio with
    tail sampling in the collector.
    """
    raw = os.environ.get("OTEL_TRACES_SAMPLER_ARG", "1.0")
    try:
        ratio = float(raw)
    except ValueError:
        ratio = 1.0
    return ParentBasedTraceIdRatio(rate=max(0.0, min(1.0, ratio)))


def continue_trace_from_meta(meta: dict | None):
    """Extract W3C Trace Context from a tools/call _meta dict.

    SEP-414 reserves `traceparent`, `tracestate`, `baggage` as the
    carrier keys for MCP. The OTEL Python propagator reads from any
    Mapping[str, str], so passing the _meta dict directly works.

    Returns an OTEL ``Context`` object suitable for
    ``tracer.start_as_current_span(context=...)``, or ``None`` if no
    trace context was present.
    """
    if not meta:
        return None
    return propagate.get_global_textmap().extract(
        carrier=meta,
        getter=DefaultGetter(),
    )


# Module-level handles for the decorator in tracing.py.
def get_tracer() -> trace.Tracer:
    return trace.get_tracer("mcp.server")


def get_duration_histogram() -> metrics.Histogram:
    return metrics.get_meter("mcp.server").create_histogram(
        name="mcp.server.operation.duration",
        description="MCP server-side operation duration",
        unit="s",
        explicit_bucket_boundaries_advisory=MCP_DURATION_BUCKETS,
    )


# Time helpers exported for tests that need to align timing with the
# decorator's measurement.
def perf_counter() -> float:
    return time.perf_counter()
