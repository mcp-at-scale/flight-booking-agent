"""Integration tests against the section3_5 server via the in-memory transport.

Unit tests in test_unit_tools.py call handlers as plain functions. These
tests go through the SDK's ClientSession bound to the real MCPServer via
in-memory streams. The protocol handshake runs. The tool-call routing
runs. The session state is the real session state. The only thing that
isn't real is the network.

Slower than the unit tests (each test pays for an initialize/handshake)
but the only layer that catches "the server starts but tool routing is
broken" or "tools/list lost a tool after a refactor."
"""

from __future__ import annotations

import pytest

from chapter3.section3_5 import mcp_server as server_module


@pytest.mark.asyncio
async def test_tools_list_includes_expected_handlers(mcp_session):
    """tools/list reports every tool the chapter3/section3_5 server registers."""
    result = await mcp_session.list_tools()
    tool_names = {t.name for t in result.tools}
    assert tool_names == {
        "search_flights",
        "hold_seat",
        "book_flight",
        "list_my_bookings",
        "search_airports",
    }


@pytest.mark.asyncio
async def test_search_flights_through_session(mcp_session):
    """tools/call routes to search_flights and the result comes back intact."""
    result = await mcp_session.call_tool(
        "search_flights",
        {"origin": "CDG", "destination": "JFK", "date": "2026-06-15"},
    )
    text = result.content[0].text
    assert "FL001" in text


@pytest.mark.asyncio
async def test_full_booking_workflow(mcp_session):
    """search -> hold -> book -> list. The workflow that the LLM drives."""
    # Search
    search = await mcp_session.call_tool(
        "search_flights",
        {"origin": "CDG", "destination": "JFK", "date": "2026-06-15"},
    )
    assert "FL001" in search.content[0].text

    # Hold
    hold = await mcp_session.call_tool(
        "hold_seat",
        {"flight_number": "FL001", "seat_number": "8A", "passenger_name": "Jane Doe"},
    )
    hold_text = hold.content[0].text
    assert hold_text.startswith("Hold")
    hold_id = hold_text.split()[1]

    # Book
    booking = await mcp_session.call_tool(
        "book_flight",
        {"hold_id": hold_id, "email": "jane@example.com", "payment_token": "tok_test"},
    )
    booking_text = booking.content[0].text
    assert "confirmed" in booking_text.lower() or "booking" in booking_text.lower()

    # List my bookings shows the new one
    listing = await mcp_session.call_tool("list_my_bookings", {})
    listing_text = listing.content[0].text
    # The just-booked flight should appear in the caller's listing.
    assert "FL001" in listing_text


@pytest.mark.asyncio
async def test_book_flight_rejects_missing_hold(mcp_session):
    """The error path is exercised through the same transport as the happy path."""
    result = await mcp_session.call_tool(
        "book_flight",
        {"hold_id": "no-such-hold", "email": "jane@example.com", "payment_token": "tok_x"},
    )
    text = result.content[0].text
    assert "not found" in text.lower()
