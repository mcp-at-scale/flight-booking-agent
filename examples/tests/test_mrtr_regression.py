"""Regression test for the §3.4 elicitation path across both protocol eras.

The 2026-07-28 revision removed server-initiated requests (SEP-2322). A server
that needs mid-call user input returns an `InputRequiredResult` and the client
retries; it can no longer call `elicitation/create` on the client. `ctx.elicit()`
therefore works only on a 2025-era connection.

§3.4 still uses `ctx.elicit()`, so `book_flight` succeeds under `mode="legacy"`
and raises under `mode="auto"`. The auto-mode test is a strict xfail: when A1
ports the example onto the `Resolve()` / `Elicit()` dependency-injection API,
it will XPASS and fail the suite, which is the signal to drop the marker.

Tracked in issue 43 (A1).
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import mcp_types as types
import pytest
from mcp.client import Client

SECTION_3_4 = (
    Path(__file__).resolve().parent.parent
    / "src"
    / "chapter3"
    / "section3_4"
    / "mcp_server.py"
)

HOLD_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f-]{27}")


def _server():
    spec = importlib.util.spec_from_file_location("_mrtr_s34", SECTION_3_4)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["_mrtr_s34"] = module
    spec.loader.exec_module(module)
    return module.mcp


async def _accept_elicitation(context, params) -> types.ElicitResult:
    """Stand in for a user who fills the form and submits."""
    return types.ElicitResult(
        action="accept",
        content={"email": "jane@example.com", "payment_token": "tok_visa_4242"},
    )


async def _book_a_flight(mode: str) -> str:
    """Hold a seat, then book it. Booking is the path that elicits."""
    async with Client(
        _server(), mode=mode, elicitation_callback=_accept_elicitation
    ) as client:
        held = await client.call_tool(
            "hold_seat",
            {
                "flight_number": "FL001",
                "seat_number": "12A",
                "passenger_name": "Jane Doe",
            },
        )
        hold_id = HOLD_ID.search(held.content[0].text)
        assert hold_id, f"no hold id in {held.content[0].text!r}"

        booked = await client.call_tool("book_flight", {"hold_id": hold_id.group(0)})
        assert not booked.is_error, booked.content[0].text
        return booked.content[0].text


@pytest.mark.anyio
async def test_elicitation_works_on_a_2025_era_connection() -> None:
    """Baseline. The example is correct for the revision it was written against."""
    assert "confirmed" in (await _book_a_flight("legacy")).lower()


@pytest.mark.anyio
@pytest.mark.xfail(
    strict=True,
    reason=(
        "§3.4 uses ctx.elicit(), which needs a server-to-client channel that "
        "2026-07-28 removed. A1 ports it to Resolve()/Elicit(); drop this marker "
        "when it starts passing."
    ),
)
async def test_elicitation_works_on_a_2026_era_connection() -> None:
    """The gap A1 closes. Auto mode negotiates 2026-07-28, where this must work."""
    assert "confirmed" in (await _book_a_flight("auto")).lower()
