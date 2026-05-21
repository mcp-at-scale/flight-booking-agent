"""Chapter 3 section 3.1: adds resource handlers via @mcp.resource().

Builds on section3_0 (which exposed one tool) by adding four read-only
resources the agent can pull for context: two static policies, an airport
lookup with a URI template parameter, and a route list. Each resource is
declared with its own decorator; the SDK infers schema + URI template
parameters from the function signature.

Run: uv run python -m chapter3.section3_1.mcp_server
"""

import json
from typing import Iterable

from mcp.server import MCPServer

from pyflight_internal.airports import get_airport_by_code, get_airports_by_country
from pyflight_internal.flights import get_all_daily_flight_templates


mcp = MCPServer(
    "flight-booking-agent",
    version="0.1.0",
    website_url="https://mcp-at-scale.com/server",
)


# ---------------------------------------------------------------------------
# Static policy text — domain content the book uses; not part of the
# pyflight_internal package because it's display-only, not flight data.
# ---------------------------------------------------------------------------

POLICIES = {
    "cancellation": (
        "Cancellation Policy\n"
        "===================\n"
        "Refundable fares: full refund up to 24 hours before departure.\n"
        "Non-refundable fares: travel credit only, minus a $75 fee.\n"
        "Award tickets: redeposit miles for a $50 fee.\n"
    ),
    "baggage": (
        "Baggage Policy\n"
        "==============\n"
        "Economy: one personal item + one carry-on (10 kg combined).\n"
        "Checked bags: first bag $30, second $50, third $150.\n"
        "Oversize/overweight: $200 each piece.\n"
    ),
}


# ---------------------------------------------------------------------------
# Resources — one decorator per URI. The SDK auto-detects the {code}
# template parameter and matches it to the function argument of the same
# name.
# ---------------------------------------------------------------------------

@mcp.resource(
    uri="flight://policies/cancellation",
    name="Cancellation Policy",
    description="Rules and fees for flight cancellations",
    mime_type="text/plain",
)
def cancellation_policy() -> str:
    return POLICIES["cancellation"]


@mcp.resource(
    uri="flight://policies/baggage",
    name="Baggage Policy",
    description="Baggage allowances and fees",
    mime_type="text/plain",
)
def baggage_policy() -> str:
    return POLICIES["baggage"]


@mcp.resource(
    uri="flight://airports/{code}",
    name="Airport Information",
    description="Details for a specific airport by IATA code",
    mime_type="application/json",
)
def airport_info(code: str) -> str:
    airport = get_airport_by_code(code.upper())
    if airport is None:
        raise ValueError(f"Airport {code!r} not found")
    return airport.model_dump_json()


@mcp.resource(
    uri="flight://routes",
    name="Available Routes",
    description="List of all bookable flight routes",
    mime_type="application/json",
)
def routes() -> str:
    templates: Iterable = get_all_daily_flight_templates()
    payload = [
        {"flight_number": t.flight_number, "origin": t.origin, "destination": t.destination}
        for t in templates
    ]
    return json.dumps(payload)


# Tool from section 3.0 stays so the running example is cumulative.
@mcp.tool()
def search_airports(country: str):
    """Search airports in a specific country (alpha-2 ISO-3166-2 code)."""
    return get_airports_by_country(country)


def main():
    mcp.run(transport="streamable-http", host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
