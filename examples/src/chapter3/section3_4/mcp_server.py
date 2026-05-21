"""Chapter 3 section 3.4: server-initiated sampling via ctx.session.create_message().

Builds on section3_3 (resources, tools, prompts) by enhancing search_flights
to ask the client's LLM to pick a recommended flight from the result set.
The server doesn't embed a model; it asks the client to run inference on
its behalf and returns the augmented result.

The `ctx: Context` parameter is auto-injected by the SDK when present in
the tool's signature. ctx.session.create_message() sends a sampling/createMessage
request to the client and returns the result. Clients that don't support
sampling raise an error caught here, so the tool degrades gracefully to
just returning the unranked flight list.

Run: uv run python -m chapter3.section3_4.mcp_server
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import SamplingMessage, TextContent

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


# Search with sampling-augmented recommendation.

@mcp.tool()
async def search_flights(
    origin: str, destination: str, date: str, ctx: Context,
) -> str:
    """Search for direct flights between two airports on a given date.

    When the client supports sampling, also asks the client's LLM to suggest
    which flight from the result set best matches a generic 'good value'
    heuristic and appends the suggestion to the response.
    """
    origin, destination = origin.strip().upper(), destination.strip().upper()
    try:
        when = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return "Error: date must be in YYYY-MM-DD format"

    flights = search_direct_flights(origin=origin, destination=destination, date=when)
    if not flights:
        return f"No direct flights from {origin} to {destination} on {date}."

    lines = [
        f"{f.flight_number}  {f.departure} -> {f.arrival}  ${f.price:.0f}  ({f.available_seats} seats)"
        for f in flights
    ]
    result = "\n".join(lines)

    # Optional sampling-augmented recommendation. If the client doesn't
    # support sampling (or any error occurs), fall through with the plain
    # flight list — we never block the search response on sampling.
    try:
        flight_brief = "\n".join(
            f"- {f.flight_number}: {f.departure} -> {f.arrival}, ${f.price:.0f}, "
            f"{f.duration_hours}h"
            for f in flights
        )
        sample = await ctx.session.create_message(
            messages=[SamplingMessage(
                role="user",
                content=TextContent(
                    type="text",
                    text=(
                        "Pick the best-value flight from the list below and explain "
                        "your reasoning in 1-2 sentences. Optimise for the shortest "
                        "time within $100 of the cheapest fare.\n\n" + flight_brief
                    ),
                ),
            )],
            max_tokens=150,
            temperature=0.3,
            system_prompt="You are a concise travel advisor.",
        )
        if isinstance(sample.content, TextContent):
            result += f"\n\n## Recommendation\n{sample.content.text}"
    except Exception:
        # Sampling not supported, timed out, or rejected by the client.
        # The flight list itself is still useful, so suppress and continue.
        pass

    return result


# Other tools (from sections 3.2 — abbreviated; see section3_3/mcp_server.py
# for the full hold_seat / book_flight / cancel_booking implementations).

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


# Prompt (from section 3.3 — one shown for the running example to stay coherent).

@mcp.prompt(description="System guidance for the flight-booking assistant.")
def flight_booking_assistant() -> list[dict[str, Any]]:
    return [{
        "role": "user",
        "content": (
            "You are a flight-booking assistant. Use the available tools to "
            "search, hold, and book; reference flight://policies/cancellation "
            "before any cancellation. Never invent flight information."
        ),
    }]


@mcp.tool()
def search_airports(country: str) -> Any:
    """Search airports in a country (alpha-2 ISO-3166-2 code)."""
    return get_airports_by_country(country)


def main():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
