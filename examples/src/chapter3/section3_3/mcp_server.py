"""Chapter 3 section 3.3: server-provided prompts via @mcp.prompt().

Builds on section3_2 (resources + tools) by adding three prompt templates
the client can fetch and feed to its LLM:

- flight_booking_assistant: persistent guidance for the whole conversation
- summarize_itinerary(booking_id): dynamic summary of a confirmed booking
- clarify_missing_info(field): elicitation helper when a tool call lacks data

Prompts return a list of message dicts; the SDK derives the prompts/list and
prompts/get protocol responses from the decorated functions automatically.

Run: uv run python -m chapter3.section3_3.mcp_server
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from mcp.server import MCPServer

from pyflight_internal.airports import get_airport_by_code, get_airports_by_country
from pyflight_internal.flights import get_flight_by_number
from pyflight_internal.search import search_direct_flights


mcp = MCPServer(
    "flight-booking-agent",
    version="0.3.0",
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


# Tools (from section 3.2 — trimmed for brevity; see section3_2/mcp_server.py
# for the full set including hold_seat / book_flight / cancel_booking).

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


# Prompts — server-provided templates that guide the client's LLM.

@mcp.prompt(
    description="System guidance for the flight-booking assistant.",
)
def flight_booking_assistant() -> list[dict[str, Any]]:
    """Comprehensive workflow guidance for the LLM running the booking session."""
    return [{
        "role": "user",
        "content": (
            "You are a flight-booking assistant. Available tools:\n"
            "- search_flights(origin, destination, date) — direct flights only\n"
            "- hold_seat(flight_number, seat_number, passenger_name) — 15 min hold\n"
            "- book_flight(hold_id, email, payment_token) — convert hold to booking\n"
            "- cancel_booking(booking_id) — only if more than 24h before departure\n\n"
            "Workflow: search -> hold -> book. Reference flight://policies/cancellation "
            "before confirming any cancellation. Never invent flight information; only "
            "use values returned by the tools."
        ),
    }]


@mcp.prompt(
    description="Dynamic summary of a confirmed itinerary, by booking_id.",
)
def summarize_itinerary(booking_id: str) -> list[dict[str, Any]]:
    """Build a friendly summary for the given booking. Arguments are substituted by
    the SDK before the prompt is returned to the client."""
    booking = BOOKINGS.get(booking_id.strip())
    if booking is None:
        return [{"role": "user", "content": f"Booking {booking_id} not found."}]
    flight = get_flight_by_number(booking["flight_number"])
    text = (
        f"Generate a friendly itinerary summary:\n"
        f"- Booking: {booking_id}\n"
        f"- Passenger: {booking['passenger_name']}\n"
        f"- Flight: {booking['flight_number']}"
    )
    if flight:
        text += f" ({flight.origin} -> {flight.destination})\n- Departure: {flight.departure}"
    text += f"\n- Seat: {booking['seat_number']}"
    return [{"role": "user", "content": text}]


@mcp.prompt(
    description="Elicit a specific missing field from the user.",
)
def clarify_missing_info(field: str) -> list[dict[str, Any]]:
    """Helper for tools that need information the user hasn't yet provided."""
    return [{
        "role": "user",
        "content": (
            f"The user wants to continue the booking but {field!r} is missing. "
            f"Ask the user for {field!r} in a single short, friendly question."
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
