"""Chapter 3 section 3.4: structured user input via @mcp.tool() + ctx.elicit().

Replaces the deprecated sampling pattern (SEP-2577 retired sampling in MCP
2026-07-28) with the elicitation/create reverse call. book_flight now collects
email + payment_token through a structured form the client renders, rather
than embedding them as tool arguments the LLM has to forward.

The `ctx: Context` parameter is auto-injected by the SDK when present in the
tool's signature. ctx.elicit() sends an elicitation/create request to the
client and returns one of three result types:
  - AcceptedElicitation: result.data is a validated Pydantic model instance
  - DeclinedElicitation: user said no
  - CancelledElicitation: user dismissed the form

Elicitation schemas must use primitive types only (str, int, float, bool, and
list[str] or Optional of these). Nested models are rejected by the SDK.

Run: uv run python -m chapter3.section3_4.mcp_server
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from mcp.server import MCPServer
from mcp.server.elicitation import (
    AcceptedElicitation,
    CancelledElicitation,
    DeclinedElicitation,
)
from mcp.server.mcpserver import Context
from pydantic import BaseModel

from pyflight_internal.airports import get_airport_by_code, get_airports_by_country
from pyflight_internal.flights import get_flight_by_number
from pyflight_internal.search import search_direct_flights


mcp = MCPServer(
    "flight-booking-agent",
    version="0.4.0",
    website_url="https://mcp-at-scale.com/server",
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


# Resources (from section 3.1)

@mcp.resource(uri="flight://policies/cancellation", name="Cancellation Policy",
              mime_type="text/plain")
def cancellation_policy() -> str:
    return POLICIES["cancellation"]


@mcp.resource(uri="flight://airports/{code}", name="Airport Information",
              mime_type="application/json")
def airport_info(code: str) -> str:
    airport = get_airport_by_code(code.upper())
    if airport is None:
        raise ValueError(f"Airport {code!r} not found")
    return airport.model_dump_json()


# Tools (from sections 3.2 / 3.3 unless noted).

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


# Elicitation: book_flight asks the user for email + payment_token through a
# client-rendered form rather than receiving them as tool arguments. The
# Pydantic schema below is the contract; the client renders a form derived
# from its JSON Schema; the server gets a validated BookingDetails back.

class BookingDetails(BaseModel):
    """Payment details collected via elicitation/create form mode."""

    email: str
    payment_token: str


@mcp.tool()
async def book_flight(hold_id: str, ctx: Context) -> str:
    """Convert a hold into a confirmed booking.

    Collects email and payment token through ctx.elicit() — a reverse call the
    server originates during this handler's execution. The client renders a
    form from BookingDetails; the user fills it in; the server resumes with
    a validated AcceptedElicitation, or short-circuits on decline / cancel.
    """
    hold = HOLDS.get(hold_id.strip())
    if hold is None:
        return (f"Error: hold {hold_id} not found "
                f"(holds expire after {HOLD_DURATION_MINUTES} minutes)")
    if hold["expires_at"] < datetime.now():
        hold["status"] = "expired"
    if hold["status"] != "active":
        return f"Error: hold is {hold['status']}, please search and hold again"

    result = await ctx.elicit(
        message=(
            f"Confirm booking for {hold['passenger_name']} on "
            f"{hold['flight_number']} (seat {hold['seat_number']}, "
            f"${hold['price']:.0f}). Provide your email and payment token."
        ),
        schema=BookingDetails,
    )
    if isinstance(result, DeclinedElicitation):
        return "Booking cancelled: user declined to provide payment details."
    if isinstance(result, CancelledElicitation):
        return "Booking cancelled: user dismissed the form."

    # AcceptedElicitation — result.data is a validated BookingDetails.
    assert isinstance(result, AcceptedElicitation)
    booking_id = str(uuid.uuid4())
    BOOKINGS[booking_id] = {
        "flight_number": hold["flight_number"],
        "seat_number": hold["seat_number"],
        "passenger_name": hold["passenger_name"],
        "email": result.data.email,
        "price": hold["price"],
        "booked_at": datetime.now(),
        "status": "confirmed",
    }
    hold["status"] = "booked"
    return (f"Booking {booking_id} confirmed for {hold['passenger_name']} on "
            f"{hold['flight_number']}, seat {hold['seat_number']}. "
            f"Confirmation emailed to {result.data.email}.")


@mcp.tool()
def cancel_booking(booking_id: str) -> str:
    """Cancel a confirmed booking. See flight://policies/cancellation for fees."""
    booking = BOOKINGS.get(booking_id.strip())
    if booking is None:
        return f"Error: booking {booking_id} not found"
    if booking["status"] != "confirmed":
        return f"Error: booking is {booking['status']}, cannot cancel"
    booking["status"] = "cancelled"
    flight = get_flight_by_number(booking["flight_number"])
    if flight:
        flight.available_seats += 1
    return f"Booking {booking_id} cancelled."


# Prompt (from §3.3 — kept so the running example stays coherent).

@mcp.prompt(description="System guidance for the flight-booking assistant.")
def flight_booking_assistant() -> list[dict[str, Any]]:
    return [{
        "role": "user",
        "content": (
            "You are a flight-booking assistant. Use the available tools to "
            "search, hold, and book; reference flight://policies/cancellation "
            "before any cancellation. Never invent flight information. "
            "book_flight collects payment details from the user via a form, "
            "so you do not need to ask for an email or payment token first."
        ),
    }]


# search_airports carried from section 3.0
@mcp.tool()
def search_airports(country: str) -> Any:
    """Search airports in a country (alpha-2 ISO-3166-2 code)."""
    return get_airports_by_country(country)


def main():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
