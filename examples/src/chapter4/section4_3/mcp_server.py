"""Chapter 4 section 4.3: ship the Flight Booking app with UI.

Cumulative on Chapter 3 section 3.5 (OAuth). Adds three MCP Apps UI
resources and modifies the booking tools to return UI references when
the caller has not supplied enough data to complete the operation.

UI resources published:
- ui://seat-map/{flight_number}: clickable seat grid. Returned when
  hold_seat is called without a seat_number. Posts hold_seat back with
  the chosen seat once the user clicks.
- ui://itinerary/{hold_id}: itinerary card with email + payment-token
  form. Returned when book_flight is called without email/payment_token.
  Posts book_flight back with the form values when the user confirms.
- ui://confirmation/{booking_id}: booking confirmation card with the
  reservation details. Returned by book_flight when the booking
  succeeds.

The wire shape follows the MCP Apps spec (2026-01-26): tools return
text content plus _meta.ui.resourceUri pointing at a separately
published resource. Hosts call resources/read to fetch the HTML.

Run: uv run python -m chapter4.section4_3.mcp_server

A demo HS256 token is printed on startup; paste it into MCP Inspector's
Authorization header to exercise the OAuth-protected tools.
"""

from __future__ import annotations

import json
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
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
# Demo HS256 TokenVerifier (carried from section 3.5)
# ---------------------------------------------------------------------------


class DemoHS256Verifier(TokenVerifier):
    """Validate HS256 JWTs minted with a shared secret. NOT FOR PRODUCTION."""

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
    """Helper to mint a demo HS256 token for local testing."""
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
# Server with OAuth wiring and UI resources
# ---------------------------------------------------------------------------

mcp = MCPServer(
    "flight-booking-agent-ui",
    version="0.6.0",
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

UI_DIR = Path(__file__).parent / "ui"


def _load_html(filename: str) -> str:
    """Load a UI template from the sibling ui/ directory."""
    return (UI_DIR / filename).read_text()


def _ui_result(text: str, resource_uri: str) -> dict:
    """Build a tool result that points the host at a UI resource."""
    return {
        "content": [{"type": "text", "text": text}],
        "_meta": {"ui": {"resourceUri": resource_uri}},
    }


# Cancellation policy resource (carried from section 3.5)
@mcp.resource(uri="flight://policies/cancellation", name="Cancellation Policy",
              mime_type="text/plain")
def cancellation_policy() -> str:
    return POLICIES["cancellation"]


# ---------------------------------------------------------------------------
# Tools that switch between text and UI based on what the caller supplies
# ---------------------------------------------------------------------------

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
def hold_seat(flight_number: str, seat_number: str | None = None,
              passenger_name: str | None = None) -> dict:
    """Hold a seat on a flight for 15 minutes.

    When called without a seat_number or passenger_name, returns the
    seat-map UI so the user can pick interactively.
    """
    token = get_access_token()
    if token is None:
        return {"content": [{"type": "text", "text": "Error: authentication required."}]}

    flight = get_flight_by_number(flight_number.strip())
    if flight is None:
        return {"content": [{"type": "text", "text": f"Error: flight {flight_number} not found."}]}

    if seat_number is None or passenger_name is None:
        return _ui_result(
            text=f"Pick a seat for flight {flight_number}.",
            resource_uri=f"ui://seat-map/{flight_number}",
        )

    if flight.available_seats <= 0:
        return {"content": [{"type": "text", "text": f"Error: no seats on {flight_number}."}]}

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
    return {"content": [{"type": "text",
                         "text": f"Hold {hold_id} created for {passenger_name} "
                                 f"on {flight_number}, seat {seat_number}."}]}


@mcp.tool()
def book_flight(hold_id: str, email: str | None = None,
                payment_token: str | None = None) -> dict:
    """Convert a hold into a confirmed booking.

    When called without email or payment_token, returns the itinerary
    card UI so the user can review the details and submit the payment
    information through a form.
    """
    token = get_access_token()
    if token is None:
        return {"content": [{"type": "text", "text": "Error: authentication required."}]}

    hold = HOLDS.get(hold_id.strip())
    if hold is None:
        return {"content": [{"type": "text", "text": f"Error: hold {hold_id} not found."}]}
    if hold["status"] != "active" or hold["expires_at"] < datetime.now():
        hold["status"] = "expired"
        return {"content": [{"type": "text", "text": "Error: hold expired."}]}

    if email is None or payment_token is None:
        return _ui_result(
            text="Review the booking and provide payment details.",
            resource_uri=f"ui://itinerary/{hold_id}",
        )

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
    return _ui_result(
        text=(f"Booking {booking_id} confirmed for {hold['passenger_name']} "
              f"on {hold['flight_number']}, seat {hold['seat_number']}."),
        resource_uri=f"ui://confirmation/{booking_id}",
    )


@mcp.tool()
def list_my_bookings() -> str:
    """List bookings made by the authenticated user."""
    token = get_access_token()
    if token is None:
        return "Error: authentication required."
    mine = [(bid, b) for bid, b in BOOKINGS.items() if b.get("user_id") == token.client_id]
    if not mine:
        return f"No bookings found for {token.client_id}."
    return "\n".join(
        f"{bid}: {b['flight_number']} seat {b['seat_number']} ({b['status']})"
        for bid, b in mine
    )


@mcp.tool()
def search_airports(country: str) -> Any:
    """Search airports in a country (alpha-2 ISO-3166-2 code)."""
    return get_airports_by_country(country)


# ---------------------------------------------------------------------------
# UI resources — published via @mcp.resource with the MCP Apps MIME type
# ---------------------------------------------------------------------------

@mcp.resource(
    uri="ui://seat-map/{flight_number}",
    name="Seat Map",
    mime_type="text/html;profile=mcp-app",
)
def seat_map_ui(flight_number: str) -> str:
    """Render the seat map for the given flight.

    Templated values:
    - {{FLIGHT_NUMBER}}: the IATA flight number the user is booking
    - {{HELD_SEATS}}: JSON array of seats already held on this flight
    """
    held = sorted(
        h["seat_number"]
        for h in HOLDS.values()
        if h["flight_number"] == flight_number and h["status"] == "active"
    )
    template = _load_html("seat_map.html")
    return (template
            .replace("{{FLIGHT_NUMBER}}", flight_number)
            .replace("{{HELD_SEATS}}", json.dumps(held)))


@mcp.resource(
    uri="ui://itinerary/{hold_id}",
    name="Itinerary Card",
    mime_type="text/html;profile=mcp-app",
)
def itinerary_ui(hold_id: str) -> str:
    """Render the itinerary review card for the given hold."""
    hold = HOLDS.get(hold_id)
    if hold is None:
        return "<!DOCTYPE html><html><body><p>Hold not found.</p></body></html>"
    template = _load_html("itinerary_card.html")
    return (template
            .replace("{{HOLD_ID}}", hold_id)
            .replace("{{FLIGHT}}", hold["flight_number"])
            .replace("{{SEAT}}", hold["seat_number"])
            .replace("{{PASSENGER}}", hold["passenger_name"])
            .replace("{{PRICE}}", f"${hold['price']:.2f}"))


@mcp.resource(
    uri="ui://confirmation/{booking_id}",
    name="Booking Confirmation",
    mime_type="text/html;profile=mcp-app",
)
def confirmation_ui(booking_id: str) -> str:
    """Render the booking confirmation card."""
    booking = BOOKINGS.get(booking_id)
    if booking is None:
        return "<!DOCTYPE html><html><body><p>Booking not found.</p></body></html>"
    template = _load_html("confirmation.html")
    return (template
            .replace("{{BOOKING_ID}}", booking_id)
            .replace("{{PASSENGER}}", booking["passenger_name"])
            .replace("{{FLIGHT}}", booking["flight_number"])
            .replace("{{SEAT}}", booking["seat_number"])
            .replace("{{EMAIL}}", booking["email"]))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    demo_token = mint_demo_token(sub="alice@example.com")
    print(f"DEMO TOKEN (paste into Inspector's Authorization header):\n{demo_token}\n")
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
