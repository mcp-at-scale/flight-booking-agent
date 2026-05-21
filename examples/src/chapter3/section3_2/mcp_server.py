"""Chapter 3 section 3.2: multi-step booking workflow via per-tool decorators.

Builds on section3_1 (resources still present) by adding the four-step booking
flow:

    search_flights → hold_seat → book_flight → cancel_booking

Each step is a separate function decorated with @mcp.tool(). The SDK
generates the tool's JSON schema from the function signature (parameter
types come from type hints; descriptions from the docstring), so the
single @server.call_tool() + 'if name == ...' router from the lowlevel
API is gone.

HOLDS and BOOKINGS are in-memory module state for the demo; production
deployments would back these with a database.

Run: uv run python -m chapter3.section3_2.mcp_server
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from mcp.server import MCPServer

from pyflight_internal.airports import get_airport_by_code, get_airports_by_country
from pyflight_internal.flights import get_all_daily_flight_templates, get_flight_by_number
from pyflight_internal.search import search_direct_flights


mcp = MCPServer(
    "flight-booking-agent",
    version="0.2.0",
    website_url="https://mcp-at-scale.com/server",
)


# ---------------------------------------------------------------------------
# Module-level session state (demo). HOLDS expires after HOLD_DURATION_MINUTES.
# ---------------------------------------------------------------------------

HOLD_DURATION_MINUTES = 15

POLICIES = {
    "cancellation": (
        "Refundable fares: full refund up to 24 hours before departure.\n"
        "Non-refundable fares: $150 cancellation fee.\n"
    ),
    "baggage": "Economy: one personal item + one carry-on (10 kg combined).",
}

HOLDS: dict[str, dict] = {}
BOOKINGS: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Resources (carried over from section 3.1)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Tools — one per function. Schema is generated from type hints; the SDK
# routes tool calls to the function whose name matches.
# ---------------------------------------------------------------------------

@mcp.tool()
def search_flights(origin: str, destination: str, date: str) -> str:
    """Search for direct flights between two airports on a given date.

    origin/destination are IATA codes (e.g. CDG, NRT). date is YYYY-MM-DD.
    """
    origin, destination = origin.strip().upper(), destination.strip().upper()
    try:
        when = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return "Error: date must be in YYYY-MM-DD format"
    if when.date() < datetime.now().date():
        return "Error: cannot search for flights in the past"
    if get_airport_by_code(origin) is None:
        return f"Error: unknown origin airport {origin!r}"
    if get_airport_by_code(destination) is None:
        return f"Error: unknown destination airport {destination!r}"

    flights = search_direct_flights(origin=origin, destination=destination, date=when)
    if not flights:
        return f"No direct flights from {origin} to {destination} on {date}."
    lines = [f"{f.flight_number}  {f.departure} -> {f.arrival}  ${f.price:.0f}  ({f.available_seats} seats)"
             for f in flights]
    return "\n".join(lines) + "\n\nUse hold_seat with a flight_number to reserve a seat."


@mcp.tool()
def hold_seat(flight_number: str, seat_number: str, passenger_name: str) -> str:
    """Hold a seat on a flight for 15 minutes pending payment.

    The hold expires automatically; cleanup runs lazily on next access.
    """
    flight = get_flight_by_number(flight_number.strip())
    if flight is None:
        return f"Error: flight {flight_number} not found"
    if flight.available_seats <= 0:
        return f"Error: no seats available on {flight_number}"

    hold_id = str(uuid.uuid4())
    expires_at = datetime.now() + timedelta(minutes=HOLD_DURATION_MINUTES)
    HOLDS[hold_id] = {
        "flight_number": flight.flight_number,
        "seat_number": seat_number.strip().upper(),
        "passenger_name": passenger_name.strip(),
        "price": flight.price,
        "expires_at": expires_at,
        "status": "active",
    }
    flight.available_seats -= 1
    return (f"Hold {hold_id} created for seat {seat_number} on {flight_number}.\n"
            f"Expires {expires_at:%Y-%m-%d %H:%M:%S}. "
            f"Use book_flight with this hold_id to complete.")


@mcp.tool()
def book_flight(hold_id: str, email: str, payment_token: str) -> str:
    """Convert a hold into a confirmed booking using the given payment token."""
    hold = HOLDS.get(hold_id.strip())
    if hold is None:
        return f"Error: hold {hold_id} not found (holds expire after {HOLD_DURATION_MINUTES} minutes)"
    if hold["status"] != "active":
        return f"Error: hold is {hold['status']}, cannot book"
    if hold["expires_at"] < datetime.now():
        hold["status"] = "expired"
        return "Error: hold has expired, please search and hold again"

    booking_id = str(uuid.uuid4())
    BOOKINGS[booking_id] = {
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
            f"{hold['flight_number']}, seat {hold['seat_number']}. "
            f"Confirmation emailed to {email}.")


@mcp.tool()
def cancel_booking(booking_id: str) -> str:
    """Cancel a confirmed booking. Cancellation fees may apply per policy.

    See the cancellation policy resource (flight://policies/cancellation).
    """
    booking = BOOKINGS.get(booking_id.strip())
    if booking is None:
        return f"Error: booking {booking_id} not found"
    if booking["status"] == "cancelled":
        return f"Error: booking {booking_id} is already cancelled"

    flight = get_flight_by_number(booking["flight_number"])
    fee = 150.00
    refund = booking["price"] - fee
    booking["status"] = "cancelled"
    booking["cancelled_at"] = datetime.now()
    if flight:
        flight.available_seats += 1
    return (f"Booking {booking_id} cancelled. "
            f"Cancellation fee ${fee:.2f}, refund ${refund:.2f} in 7-10 business days.")


# Tool carried over from section 3.0
@mcp.tool()
def search_airports(country: str) -> Any:
    """Search airports in a specific country (alpha-2 ISO-3166-2 code)."""
    return get_airports_by_country(country)


def main():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
