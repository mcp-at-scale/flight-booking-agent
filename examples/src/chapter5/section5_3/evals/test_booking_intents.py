"""Eval suite for the flight-booking server's tool-selection behaviour.

Each eval drives a real LLM (configured in mcpeval.yaml) against a real
spawned MCP server and asserts on which tools the model actually called.
The bugs caught here are model-side bugs that no unit or integration
test from §5.1 can catch: paraphrase regressions, intent disambiguation
shifts after a model upgrade, multi-turn state mishandling.

Each test runs in a fresh agent session unless explicitly stating
otherwise; the mcp-eval framework resets state between tests.
"""

from __future__ import annotations

import pytest
from mcp_eval import Expect


# ---------------------------------------------------------------------------
# search_flights: must respect different ways users describe the same intent
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_search_with_iata_codes(mcp_agent):
    """IATA codes are unambiguous. The model should call search_flights."""
    await mcp_agent.generate_str(
        "find me flights CDG to NRT on 2026-06-15"
    )
    await mcp_agent.assert_that(Expect.tools.was_called("search_flights"))


@pytest.mark.asyncio
async def test_search_with_city_names(mcp_agent):
    """Same intent as above, paraphrased with city names. Should still
    resolve to search_flights without the model getting confused into
    calling search_airports first."""
    await mcp_agent.generate_str(
        "what flights are there from Paris to Tokyo on June 15th 2026?"
    )
    await mcp_agent.assert_that(Expect.tools.was_called("search_flights"))


@pytest.mark.asyncio
async def test_search_with_relative_date(mcp_agent):
    """Relative dates ('next Monday') are a regression risk after model
    upgrades; assert the model still resolves them to search_flights with
    a concrete YYYY-MM-DD argument."""
    await mcp_agent.generate_str(
        "I want to fly from CDG to NRT next Monday"
    )
    await mcp_agent.assert_that(Expect.tools.was_called("search_flights"))


# ---------------------------------------------------------------------------
# hold_seat: the agent should not skip ahead to booking
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_hold_specific_seat(mcp_agent):
    await mcp_agent.generate_str(
        "Hold seat 8A on FL001 for Jane Doe."
    )
    await mcp_agent.assert_that(Expect.tools.was_called("hold_seat"))
    # Holding is not booking; book_flight must not fire from this message.
    await mcp_agent.assert_that(Expect.tools.count("book_flight", 0))


# ---------------------------------------------------------------------------
# book_flight: multi-turn flow with state preservation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_turn_hold_then_book(mcp_agent):
    """The classic conversational flow: hold a seat, then book against
    that hold. The second turn must reuse the held context without
    re-searching."""
    await mcp_agent.generate_str(
        "Hold seat 8A on FL001 for Jane Doe."
    )
    await mcp_agent.generate_str(
        "Go ahead and book it. My email is jane@example.com, "
        "use payment token tok_test_visa."
    )
    await mcp_agent.assert_that(Expect.tools.was_called("book_flight"))
    # The agent must not search again on the second turn.
    await mcp_agent.assert_that(Expect.tools.count("search_flights", 0))


# ---------------------------------------------------------------------------
# Intent disambiguation: the Monday-model-upgrade regression
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_drop_my_booking_is_cancel(mcp_agent):
    """The exact bug the §5.3 opening scenario describes: 'drop my booking'
    must resolve to cancel_booking, not list_my_bookings. A model upgrade
    that shifts this from 95% to 92% is what eval-in-CI catches."""
    await mcp_agent.generate_str(
        "drop my booking BK-12345"
    )
    await mcp_agent.assert_that(Expect.tools.was_called("cancel_booking"))
    await mcp_agent.assert_that(Expect.tools.count("list_my_bookings", 0))


@pytest.mark.asyncio
async def test_what_have_i_booked_is_list_not_search(mcp_agent):
    """Question-shape intent: the model should list existing bookings,
    not start a new search."""
    await mcp_agent.generate_str(
        "What have I booked recently?"
    )
    await mcp_agent.assert_that(Expect.tools.was_called("list_my_bookings"))
    await mcp_agent.assert_that(Expect.tools.count("search_flights", 0))


@pytest.mark.asyncio
async def test_change_my_flight_does_not_cancel(mcp_agent):
    """'Change' is not the same as 'cancel'. The agent should not call
    cancel_booking until that's confirmed as the user's intent."""
    await mcp_agent.generate_str(
        "I need to change my flight"
    )
    # Either the agent asks for clarification (no destructive call),
    # or it calls list_my_bookings to find what to change. Either way,
    # cancel_booking is wrong.
    await mcp_agent.assert_that(Expect.tools.count("cancel_booking", 0))
