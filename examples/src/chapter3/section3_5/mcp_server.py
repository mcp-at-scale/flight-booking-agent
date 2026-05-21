"""Chapter 3 section 3.5: OAuth via MCPServer(token_verifier=..., auth=...).

Builds on section3_4 (resources, tools, prompts, sampling) by enabling OAuth
authentication. The SDK ships TokenVerifier as a Protocol; this section
demonstrates a *demo* HS256 verifier (shared-secret, for local testing only).
Section 6.2 of the book replaces this with a production-grade RS256/JWKS
verifier — same MCPServer wiring, more robust verifier implementation.

Tools read the authenticated user from
mcp.server.auth.middleware.auth_context.get_access_token() and attribute
state changes (bookings) to that user.

Run: uv run python -m chapter3.section3_5.mcp_server

Mint a demo token for local testing (see the docstring for DemoHS256Verifier
below for the exact claims structure).
"""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# Demo HS256 TokenVerifier — local development only.
#
# Section 6.2 of the book replaces this with JWKSTokenVerifier (RS256 +
# provider JWKS endpoint + key rotation). The MCPServer wiring below stays
# identical; only this class swaps.
# ---------------------------------------------------------------------------


class DemoHS256Verifier(TokenVerifier):
    """Validate HS256 JWTs minted with a shared secret. NOT FOR PRODUCTION.

    Expected claims:
        sub: user identifier (becomes AccessToken.client_id)
        scope: space-separated scopes
        aud: must equal DEMO_AUDIENCE
        iss: must equal DEMO_ISSUER
        exp: standard expiry
    """

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
    """Helper to mint a demo HS256 token for local testing.

    Example:
        token = mint_demo_token(sub="alice@example.com")
    """
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
# MCPServer with OAuth wired in
# ---------------------------------------------------------------------------

mcp = MCPServer(
    "flight-booking-agent",
    version="0.5.0",
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


@mcp.tool()
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
def book_flight(hold_id: str, email: str, payment_token: str) -> str:
    """Convert a hold into a confirmed booking attributed to the authenticated user.

    The authenticated user's client_id is read from
    mcp.server.auth.middleware.auth_context.get_access_token() and stamped
    onto the booking record.
    """
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
    return (f"Booking {booking_id} confirmed for {hold['passenger_name']}. "
            f"Attributed to user {token.client_id}.")


@mcp.tool()
def list_my_bookings() -> str:
    """List bookings made by the authenticated user."""
    token = get_access_token()
    if token is None:
        return "Error: authentication required"

    mine = [b for b in BOOKINGS.values() if b.get("user_id") == token.client_id]
    if not mine:
        return f"No bookings found for {token.client_id}."
    return "\n".join(
        f"{b.get('booked_at', '?')}: {b['flight_number']} seat {b['seat_number']}"
        for b in mine
    )


@mcp.tool()
def hold_seat(flight_number: str, seat_number: str, passenger_name: str) -> str:
    """Hold a seat on a flight for 15 minutes pending payment."""
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
    }
    flight.available_seats -= 1
    return f"Hold {hold_id} created for {flight_number}."


@mcp.tool()
def search_airports(country: str) -> Any:
    """Search airports in a country (alpha-2 ISO-3166-2 code)."""
    return get_airports_by_country(country)


def main():
    # Demo: print a usable token so you can paste it into MCP Inspector.
    print(f"DEMO TOKEN for sub=alice@example.com:\n  {mint_demo_token(sub='alice@example.com')}\n")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
