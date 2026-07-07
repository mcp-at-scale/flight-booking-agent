"""Unit tests for the chapter3/section3_5 tool handlers.

These call each tool function as a normal Python callable. The
@mcp.tool() decorator registers the function with the server but does
not transform it; the function still accepts its declared arguments
and returns its declared value. That makes unit tests cheap.

For tools that read from get_access_token(), the `authenticated` and
`unauthenticated` fixtures (defined in conftest.py) patch the lookup
so the test controls whether the request looks authenticated or not.
"""

from __future__ import annotations

from chapter3.section3_5 import mcp_server as server


# ---------------------------------------------------------------------------
# search_flights: no auth required
# ---------------------------------------------------------------------------

def test_search_flights_returns_results_for_known_route():
    result = server.search_flights(origin="CDG", destination="JFK", date="2026-06-15")
    assert "FL001" in result
    assert "->" in result


def test_search_flights_rejects_malformed_date():
    result = server.search_flights(origin="CDG", destination="NRT", date="not-a-date")
    assert result.startswith("Error: date must be in YYYY-MM-DD format")


def test_search_flights_handles_no_matches():
    result = server.search_flights(origin="CDG", destination="ZZZ", date="2026-06-15")
    assert "No direct flights" in result


# ---------------------------------------------------------------------------
# hold_seat: requires authentication
# ---------------------------------------------------------------------------

def test_hold_seat_requires_authentication(unauthenticated):
    result = server.hold_seat(
        flight_number="FL001", seat_number="8A", passenger_name="Jane Doe",
    )
    assert "authentication required" in result.lower()


def test_hold_seat_rejects_unknown_flight(authenticated):
    result = server.hold_seat(
        flight_number="ZZZ999", seat_number="8A", passenger_name="Jane Doe",
    )
    assert "cannot hold ZZZ999" in result


def test_hold_seat_creates_hold_for_authenticated_user(authenticated):
    result = server.hold_seat(
        flight_number="FL001", seat_number="8A", passenger_name="Jane Doe",
    )
    assert "Hold" in result
    assert "FL001" in result
    # The hold registry now contains the new hold.
    assert len(server.HOLDS) == 1


# ---------------------------------------------------------------------------
# book_flight: requires hold, requires authentication
# ---------------------------------------------------------------------------

def test_book_flight_requires_authentication(unauthenticated):
    result = server.book_flight(
        hold_id="any-hold", email="jane@example.com", payment_token="tok_x",
    )
    assert "authentication required" in result.lower()


def test_book_flight_rejects_unknown_hold(authenticated):
    result = server.book_flight(
        hold_id="not-a-real-hold",
        email="jane@example.com",
        payment_token="tok_x",
    )
    assert "hold" in result.lower() and "not found" in result.lower()


def test_book_flight_completes_for_valid_hold(authenticated):
    # Set up: create a hold first.
    hold_result = server.hold_seat(
        flight_number="FL001", seat_number="8A", passenger_name="Jane Doe",
    )
    hold_id = _extract_hold_id(hold_result)
    assert hold_id

    # Act: book against that hold.
    booking_result = server.book_flight(
        hold_id=hold_id, email="jane@example.com", payment_token="tok_test",
    )

    # Assert: booking registry has one entry attributed to the test user.
    assert "confirmed" in booking_result.lower() or "booking" in booking_result.lower()
    assert len(server.BOOKINGS) == 1
    only_booking = next(iter(server.BOOKINGS.values()))
    assert only_booking["user_id"] == "alice@example.com"


# ---------------------------------------------------------------------------
# list_my_bookings: scopes to the authenticated user
# ---------------------------------------------------------------------------

def test_list_my_bookings_is_empty_for_new_user(authenticated):
    result = server.list_my_bookings()
    assert "No bookings" in result


def test_list_my_bookings_returns_only_callers_bookings(authenticated):
    # Set up: a booking belonging to a different user (synthesised directly).
    server.BOOKINGS["other-booking"] = {
        "user_id": "bob@example.com",
        "flight_number": "FL002",
        "seat_number": "12B",
        "passenger_name": "Bob",
        "email": "bob@example.com",
        "price": 100,
        "status": "confirmed",
    }
    # Set up: a booking belonging to our authenticated user (alice).
    server.BOOKINGS["alice-booking"] = {
        "user_id": "alice@example.com",
        "flight_number": "FL001",
        "seat_number": "8A",
        "passenger_name": "Alice",
        "email": "alice@example.com",
        "price": 100,
        "status": "confirmed",
    }

    result = server.list_my_bookings()
    assert "FL001" in result       # alice's own booking is listed
    assert "FL002" not in result   # bob's booking is excluded


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _extract_hold_id(text: str) -> str:
    """The hold_seat result text is 'Hold <uuid> created for FL001.' or similar."""
    parts = text.split()
    if len(parts) < 2 or parts[0] != "Hold":
        return ""
    return parts[1]
