"""
Sample flight data for the flight booking system.
All flights are defined with unique flight numbers for each route and time slot.
All flights operate daily.
"""

from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
import json
import random
from pyflight_internal.models import FlightTemplate, Flight


# Load flight templates data
_DATA_DIR = Path(__file__).parent / "data"
_flight_templates_cache: Optional[list[FlightTemplate]] = None


def _load_flight_templates() -> list[FlightTemplate]:
    """Load flight templates from JSON file."""
    global _flight_templates_cache
    if _flight_templates_cache is None:
        with open(_DATA_DIR / "flights.json", "r") as f:
            data = json.load(f)
            _flight_templates_cache = [FlightTemplate(**template) for template in data]
    return _flight_templates_cache


def get_flight_for_date(flight_template: FlightTemplate, date: datetime) -> Flight:
    """
    Generate a specific flight instance for a given date.

    Args:
        flight_template: FlightTemplate object
        date: Date for this flight instance

    Returns:
        Flight instance with specific date/time
    """
    # Parse departure time
    hour, minute = map(int, flight_template.departure_time.split(":"))
    departure_datetime = date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    arrival_datetime = departure_datetime + timedelta(hours=flight_template.duration_hours)

    # Price variation based on day of week
    price_multiplier = 1.0
    if departure_datetime.weekday() in [4, 5, 6]:  # Weekend
        price_multiplier += 0.2
    if hour == 6:  # Morning flight
        price_multiplier += 0.1

    # Simulate varying seat availability (deterministic based on date and flight)
    random.seed(f"{flight_template.flight_number}-{date.toordinal()}")
    available_seats = random.randint(50, 180)

    return Flight(
        flight_number=flight_template.flight_number,
        airline=flight_template.airline,
        origin=flight_template.origin,
        destination=flight_template.destination,
        departure=departure_datetime.isoformat(),
        arrival=arrival_datetime.isoformat(),
        duration_hours=flight_template.duration_hours,
        price=round(flight_template.base_price * price_multiplier, 2),
        currency="USD",
        available_seats=available_seats,
        total_seats=180,
        status="scheduled" if available_seats > 0 else "sold_out",
    )


def get_flights_by_route(origin: str, destination: str, date: datetime) -> list[Flight]:
    """
    Get all flights for a specific route on a specific date.

    Args:
        origin: Origin airport code
        destination: Destination airport code
        date: Date to get flights for

    Returns:
        List of flights for that route on that date
    """
    flight_templates = _load_flight_templates()
    matching_templates = [
        flight for flight in flight_templates
        if flight.origin == origin and flight.destination == destination
    ]

    flights = []
    for template in matching_templates:
        flight = get_flight_for_date(template, date)
        flights.append(flight)

    # Sort by departure time
    flights.sort(key=lambda x: x.departure)
    return flights


def get_flight_by_number(flight_number: str, date: Optional[datetime] = None) -> Optional[Flight]:
    """
    Get a specific flight by flight number on a given date.

    Args:
        flight_number: Unique flight number
        date: Date to get flight for (defaults to today)

    Returns:
        Flight instance if found, None otherwise
    """
    if date is None:
        date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Find the flight template
    flight_templates = _load_flight_templates()
    flight_template = next(
        (f for f in flight_templates if f.flight_number == flight_number),
        None
    )

    if not flight_template:
        return None

    return get_flight_for_date(flight_template, date)


def get_all_flights_for_date(date: datetime) -> list[Flight]:
    """
    Get all flights operating on a specific date.

    Args:
        date: Date to get flights for

    Returns:
        List of all flights on that date
    """
    flight_templates = _load_flight_templates()
    flights = []
    for template in flight_templates:
        flight = get_flight_for_date(template, date)
        flights.append(flight)

    flights.sort(key=lambda x: (x.origin, x.destination, x.departure))
    return flights


def get_all_daily_flight_templates() -> list[FlightTemplate]:
    """
    Get all daily flight templates.

    Returns:
        List of all flight templates that operate daily
    """
    return _load_flight_templates().copy()
