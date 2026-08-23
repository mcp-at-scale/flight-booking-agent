"""Structured tool-call logger for Chapter 5 §5.2.

Defines the minimum structured log shape one tools/call invocation
produces. The shape is forward-compatible with the AuditEvent class
Chapter 6 §6.5 ships in code/security/flight_booking_audit.py: same
field names, same JSON shape, same correlation-ID semantics. The
Chapter 6 version adds client_id / scopes from the OAuth context and
replaces the naive sanitization helpers here with PII-aware ones.

Use the decorator outside @mcp.tool() so the SDK's registration sees
the wrapped function:

    @mcp.tool()
    @log_tool_call(emit=write_to_stdout)
    def search_flights(origin: str, destination: str, date: str) -> str:
        ...
"""

from __future__ import annotations

import json
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable

# Argument values longer than this are truncated in the log to keep
# log lines small. Production deployments would tune this per-tool.
ARG_TRUNCATE_LEN = 128

# Result summary clipped at this many characters before emission.
RESULT_SUMMARY_LEN = 200


@dataclass
class ToolCallLog:
    """One structured row per tool invocation.

    Field semantics:
    - timestamp: UTC ISO 8601 with milliseconds
    - request_id: 11-char correlation key generated per call
    - tool_name: the @mcp.tool() function name
    - arguments: positional + keyword args; long string values truncated
    - decision: "success" | "error:<ExceptionClassName>"
    - latency_ms: handler-entry to handler-exit elapsed time
    - result_summary: truncated str() of the return value
    - result_type: "complete" for an answer, "input_required" when the server
      returned a question instead and expects the client to call again
      (multi round-trip requests, see ch3 3.4). A round trip produces two
      rows for one user-visible action; this field is what distinguishes
      that pair from a genuine duplicate call.
    """

    timestamp: str
    request_id: str
    tool_name: str
    arguments: dict
    decision: str
    latency_ms: int
    result_summary: str = ""
    result_type: str = "complete"

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"))


def log_tool_call(emit: Callable[[str], None] | None = None):
    """Decorator: wrap an @mcp.tool() handler with structured logging.

    Args:
        emit: callable that receives one JSON line per tool call. If None,
            defaults to writing one line to stdout. Production should pass
            a SIEM/log-aggregator emitter (Datadog, Splunk, Loki, etc.).
    """
    if emit is None:
        emit = lambda line: sys.stdout.write(line + "\n")

    def decorator(handler):
        def wrapper(*args, **kwargs):
            request_id = uuid.uuid4().hex[:11]
            started = time.perf_counter()
            decision = "success"
            result: Any = None
            try:
                result = handler(*args, **kwargs)
                return result
            except Exception as exc:
                decision = f"error:{type(exc).__name__}"
                raise
            finally:
                latency_ms = int((time.perf_counter() - started) * 1000)
                event = ToolCallLog(
                    timestamp=datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                    request_id=request_id,
                    tool_name=handler.__name__,
                    arguments=_safe_arguments(args, kwargs),
                    decision=decision,
                    latency_ms=latency_ms,
                    result_summary=_summarize(result),
                )
                try:
                    emit(event.to_json())
                except Exception:
                    # Never let a logging failure mask the handler's outcome.
                    pass

        wrapper.__name__ = handler.__name__
        wrapper.__doc__ = handler.__doc__
        wrapper.__wrapped__ = handler  # so pytest can find the underlying fn
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Helpers (intentionally simple; Chapter 6 §6.5 replaces them with
# PII-aware versions in code/security/flight_booking_audit.py)
# ---------------------------------------------------------------------------


def _safe_arguments(args: tuple, kwargs: dict) -> dict:
    """Build a JSON-serializable dict from the handler's positional + kw args.

    - Positional args are recorded under "args" as a list of repr strings.
    - Keyword args are recorded under their parameter names.
    - String values longer than ARG_TRUNCATE_LEN are truncated.
    - Non-JSON-serializable values fall back to repr().
    """
    out: dict[str, Any] = {}
    if args:
        out["args"] = [_truncate(_to_json_safe(a)) for a in args]
    for k, v in kwargs.items():
        out[k] = _truncate(_to_json_safe(v))
    return out


def _to_json_safe(value: Any) -> Any:
    """Reduce a Python value to something json.dumps will accept."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_to_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(k): _to_json_safe(v) for k, v in value.items()}
    return repr(value)


def _truncate(value: Any) -> Any:
    if isinstance(value, str) and len(value) > ARG_TRUNCATE_LEN:
        return value[:ARG_TRUNCATE_LEN] + "..."
    return value


def _summarize(result: Any) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        text = result
    else:
        try:
            text = json.dumps(result, default=repr, separators=(",", ":"))
        except (TypeError, ValueError):
            text = repr(result)
    if len(text) > RESULT_SUMMARY_LEN:
        text = text[:RESULT_SUMMARY_LEN] + "..."
    return text
