"""@otel_trace_tool decorator for Chapter 5 §5.4.

Wraps an @mcp.tool() handler with an OpenTelemetry span sized per the
semantic conventions at https://opentelemetry.io/docs/specs/semconv/gen-ai/mcp/
and a histogram measurement of mcp.server.operation.duration.

Stack outside @mcp.tool() and outside the @log_tool_call decorator from
section5_2 so spans surround both registration and structured logging:

    @mcp.tool()
    @otel_trace_tool()
    @log_tool_call()
    def book_flight(...): ...

The decorator reads tracer + meter handles via OTEL's global lookup, so
``setup_otel()`` from otel_setup.py must run once before this is used.
"""

from __future__ import annotations

import time
from typing import Callable

from opentelemetry import trace

from chapter5.section5_4.otel_setup import (
    continue_trace_from_meta,
    get_duration_histogram,
    get_tracer,
)


def otel_trace_tool() -> Callable:
    """Decorator: wrap a tool handler with an OTEL span + duration histogram.

    Span shape (OpenTelemetry MCP semantic conventions):
      - Name: ``tools/call <tool_name>``
      - Kind: SERVER
      - Attributes: mcp.method.name, gen_ai.operation.name,
        gen_ai.tool.name, plus error.type on exceptions
    """

    def decorator(handler):
        tracer = get_tracer()
        duration = get_duration_histogram()

        def wrapper(*args, ctx=None, **kwargs):
            # Pull W3C trace context out of _meta per SEP-414. If the
            # caller (host -> client) sent traceparent, we continue the
            # existing trace; otherwise we start a new one.
            meta = (ctx.request_context.meta if ctx is not None else {}) or {}
            parent_ctx = continue_trace_from_meta(meta)

            span_attrs = {
                "mcp.method.name": "tools/call",
                "gen_ai.operation.name": "execute_tool",
                "gen_ai.tool.name": handler.__name__,
            }

            started = time.perf_counter()
            with tracer.start_as_current_span(
                f"tools/call {handler.__name__}",
                kind=trace.SpanKind.SERVER,
                context=parent_ctx,
                attributes=span_attrs,
            ) as span:
                try:
                    if ctx is not None:
                        result = handler(*args, ctx=ctx, **kwargs)
                    else:
                        result = handler(*args, **kwargs)
                    span.set_status(trace.Status(trace.StatusCode.OK))
                    return result
                except Exception as exc:
                    span.set_status(
                        trace.Status(trace.StatusCode.ERROR, description=str(exc))
                    )
                    span.set_attribute("error.type", type(exc).__name__)
                    raise
                finally:
                    elapsed = time.perf_counter() - started
                    duration.record(
                        elapsed,
                        attributes={"gen_ai.tool.name": handler.__name__},
                    )

        wrapper.__name__ = handler.__name__
        wrapper.__doc__ = handler.__doc__
        wrapper.__wrapped__ = handler
        return wrapper

    return decorator
