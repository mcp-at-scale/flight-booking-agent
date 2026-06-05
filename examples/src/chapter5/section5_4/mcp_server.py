"""Chapter 5 section 5.4: production observability with SEP-414 + OpenTelemetry.

Cumulative on chapter5/section5_2 (structured logging). Adds:

  - OTLP-exported OpenTelemetry traces with W3C Trace Context propagation
    via SEP-414 (_meta.traceparent / tracestate / baggage)
  - An mcp.server.operation.duration histogram metric per the
    OpenTelemetry semantic conventions for MCP
  - A @otel_trace_tool decorator stacked alongside the @log_tool_call
    decorator from section5_2

Run a local OTLP collector first (e.g. Jaeger's all-in-one image, the
OpenTelemetry Collector, or a vendor APM):

    docker run -d --name jaeger -p 4317:4317 -p 16686:16686 \\
        jaegertracing/all-in-one:latest

Then start the server with the collector address:

    export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
    uv run python -m chapter5.section5_4.mcp_server

Exercise a tool through MCP Inspector and watch the trace appear at
http://localhost:16686 (Jaeger) or your collector of choice.
"""

from __future__ import annotations

import sys
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

import jwt
from pydantic import AnyHttpUrl

from mcp.server import MCPServer
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings

from pyflight_internal.airports import get_airport_by_code, get_airports_by_country
from pyflight_internal.flights import get_flight_by_number
from pyflight_internal.search import search_direct_flights

from chapter5.section5_2.structured_logger import log_tool_call
from chapter5.section5_4.otel_setup import setup_otel
from chapter5.section5_4.tracing import otel_trace_tool


# Configure OTEL once at process import; the @otel_trace_tool decorator
# reads tracer/meter via the global providers we set here.
setup_otel()


# ---------------------------------------------------------------------------
# Demo HS256 TokenVerifier (unchanged from §3.5)
# ---------------------------------------------------------------------------


class DemoHS256Verifier(TokenVerifier):
    DEMO_SECRET = "demo-secret-do-not-use-in-production"
    DEMO_AUDIENCE = "flight-booking-mcp-server"
    DEMO_ISSUER = "https://demo-issuer.example.com/"

    async def verify_token(self, token: str) -> AccessToken | None:
        try:
            payload = jwt.decode(
                token, self.DEMO_SECRET,
                algorithms=["HS256"],
                audience=self.DEMO_AUDIENCE,
                issuer=self.DEMO_ISSUER,
                options={"verify_exp": True, "require": ["exp", "sub"]},
            )
        except jwt.InvalidTokenError:
            return None
        raw_scope = payload.get("scope") or payload.get("scopes") or ""
        scopes = raw_scope.split() if isinstance(raw_scope, str) else list(raw_scope)
        return AccessToken(
            token=token,
            client_id=payload["sub"],
            scopes=scopes,
            expires_at=payload.get("exp"),
        )


def mint_demo_token(*, sub: str, scope: str = "openid read:bookings write:bookings",
                    lifetime_seconds: int = 3600) -> str:
    now = int(time.time())
    payload = {
        "iss": DemoHS256Verifier.DEMO_ISSUER,
        "aud": DemoHS256Verifier.DEMO_AUDIENCE,
        "sub": sub,
        "scope": scope,
        "iat": now,
        "exp": now + lifetime_seconds,
    }
    return jwt.encode(payload, DemoHS256Verifier.DEMO_SECRET, algorithm="HS256")


# ---------------------------------------------------------------------------
# Server wiring (same OAuth shape as §3.5 and §5.2)
# ---------------------------------------------------------------------------


mcp = MCPServer(
    "flight-booking-agent-traced",
    version="0.5.4",
    website_url="https://mcp-at-scale.com/server",
    token_verifier=DemoHS256Verifier(),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(DemoHS256Verifier.DEMO_ISSUER),
        resource_server_url=AnyHttpUrl("http://localhost:9000"),
        required_scopes=["openid", "read:bookings"],
    ),
)


HOLD_DURATION_MINUTES = 15
POLICIES = {
    "cancellation": (
        "Refundable fares: full refund up to 24 hours before departure.\n"
        "Non-refundable fares: $150 cancellation fee.\n"
    ),
}
HOLDS: dict[str, dict] = {}
BOOKINGS: dict[str, dict] = {}


@mcp.resource(uri="flight://policies/cancellation", name="Cancellation Policy",
              mime_type="text/plain")
def cancellation_policy() -> str:
    return POLICIES["cancellation"]


# ---------------------------------------------------------------------------
# Tools stacked with @otel_trace_tool (outer) + @log_tool_call (inner)
# ---------------------------------------------------------------------------


@mcp.tool()
@otel_trace_tool()
@log_tool_call()
def search_flights(origin: str, destination: str, date: str) -> str:
    """Search for direct flights between two airports on a given date."""
    origin, destination = origin.strip().upper(), destination.strip().upper()
    try:
        when = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return "Error: date must be in YYYY-MM-DD format"
    flights = search_direct_flights(origin=origin, destination=destination, date=when)
    if not flights:
        return f"No direct flights from {origin} to {destination} on {date}."
    return "\n".join(
        f"{f.flight_number}  {f.departure} -> {f.arrival}  ${f.price:.0f}"
        for f in flights
    )


@mcp.tool()
@otel_trace_tool()
@log_tool_call()
def hold_seat(flight_number: str, seat_number: str, passenger_name: str) -> str:
    """Hold a seat on a flight for 15 minutes pending payment."""
    token = get_access_token()
    if token is None:
        return "Error: authentication required"
    flight = get_flight_by_number(flight_number.strip())
    if flight is None or flight.available_seats <= 0:
        return f"Error: cannot hold {flight_number}"
    hold_id = str(uuid.uuid4())
    HOLDS[hold_id] = {
        "flight_number": flight.flight_number,
        "seat_number": seat_number.strip().upper(),
        "passenger_name": passenger_name.strip(),
        "price": flight.price,
        "expires_at": datetime.now() + timedelta(minutes=HOLD_DURATION_MINUTES),
        "status": "active",
        "user_id": token.client_id,
    }
    flight.available_seats -= 1
    return f"Hold {hold_id} created for {flight_number}."


@mcp.tool()
@otel_trace_tool()
@log_tool_call()
def book_flight(hold_id: str, email: str, payment_token: str) -> str:
    """Convert a hold into a confirmed booking attributed to the authenticated user."""
    token = get_access_token()
    if token is None:
        return "Error: authentication required"
    hold = HOLDS.get(hold_id.strip())
    if hold is None:
        return f"Error: hold {hold_id} not found"
    if hold["status"] != "active" or hold["expires_at"] < datetime.now():
        return "Error: hold is expired or already used"
    booking_id = str(uuid.uuid4())
    BOOKINGS[booking_id] = {
        "user_id": token.client_id,
        "flight_number": hold["flight_number"],
        "seat_number": hold["seat_number"],
        "passenger_name": hold["passenger_name"],
        "email": email.strip(),
        "price": hold["price"],
        "booked_at": datetime.now(),
        "status": "confirmed",
    }
    hold["status"] = "booked"
    return (f"Booking {booking_id} confirmed for {hold['passenger_name']} on "
            f"{hold['flight_number']}.")


@mcp.tool()
@otel_trace_tool()
@log_tool_call()
def list_my_bookings() -> str:
    """List bookings made by the authenticated user."""
    token = get_access_token()
    if token is None:
        return "Error: authentication required"
    mine = [(bid, b) for bid, b in BOOKINGS.items() if b.get("user_id") == token.client_id]
    if not mine:
        return f"No bookings found for {token.client_id}."
    return "\n".join(
        f"{bid}: {b['flight_number']} seat {b['seat_number']} ({b['status']})"
        for bid, b in mine
    )


@mcp.tool()
@otel_trace_tool()
@log_tool_call()
def search_airports(country: str) -> Any:
    """Search airports in a country (alpha-2 ISO-3166-2 code)."""
    return get_airports_by_country(country)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    demo_token = mint_demo_token(sub="alice@example.com")
    print(f"DEMO TOKEN (paste into Inspector's Authorization header):\n{demo_token}\n",
          file=sys.stderr)
    endpoint = (
        "OTLP exporter -> "
        f"{__import__('os').environ.get('OTEL_EXPORTER_OTLP_ENDPOINT', '(default, gRPC localhost:4317)')}"
    )
    print(endpoint, file=sys.stderr)
    print("Tool call logs follow (one JSON line per @mcp.tool() invocation):",
          file=sys.stderr)
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
