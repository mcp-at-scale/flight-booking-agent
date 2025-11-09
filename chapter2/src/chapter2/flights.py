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
from chapter2.models import FlightTemplate, Flight


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


# Daily flight schedule - each flight operates every day at the same time
# Format: Each route has 3 flights per day (morning, afternoon, evening)
# DEPRECATED: This list is kept for reference only. Use _load_flight_templates() instead.
OLD_DAILY_FLIGHTS = [
    # Europe <-> USA
    # CDG -> JFK
    {"flight_number": "FL001", "airline": "FL", "origin": "CDG", "destination": "JFK", "departure_time": "06:00", "duration_hours": 8.5, "base_price": 650},
    {"flight_number": "FL003", "airline": "FL", "origin": "CDG", "destination": "JFK", "departure_time": "14:00", "duration_hours": 8.5, "base_price": 650},
    {"flight_number": "FL005", "airline": "FL", "origin": "CDG", "destination": "JFK", "departure_time": "22:00", "duration_hours": 8.5, "base_price": 650},
    # JFK -> CDG
    {"flight_number": "FL002", "airline": "FL", "origin": "JFK", "destination": "CDG", "departure_time": "06:00", "duration_hours": 7.5, "base_price": 680},
    {"flight_number": "FL004", "airline": "FL", "origin": "JFK", "destination": "CDG", "departure_time": "14:00", "duration_hours": 7.5, "base_price": 680},
    {"flight_number": "FL006", "airline": "FL", "origin": "JFK", "destination": "CDG", "departure_time": "22:00", "duration_hours": 7.5, "base_price": 680},

    # LHR <-> JFK
    {"flight_number": "BS101", "airline": "BS", "origin": "LHR", "destination": "JFK", "departure_time": "06:00", "duration_hours": 8.0, "base_price": 620},
    {"flight_number": "BS103", "airline": "BS", "origin": "LHR", "destination": "JFK", "departure_time": "14:00", "duration_hours": 8.0, "base_price": 620},
    {"flight_number": "BS105", "airline": "BS", "origin": "LHR", "destination": "JFK", "departure_time": "22:00", "duration_hours": 8.0, "base_price": 620},
    {"flight_number": "BS102", "airline": "BS", "origin": "JFK", "destination": "LHR", "departure_time": "06:00", "duration_hours": 7.0, "base_price": 640},
    {"flight_number": "BS104", "airline": "BS", "origin": "JFK", "destination": "LHR", "departure_time": "14:00", "duration_hours": 7.0, "base_price": 640},
    {"flight_number": "BS106", "airline": "BS", "origin": "JFK", "destination": "LHR", "departure_time": "22:00", "duration_hours": 7.0, "base_price": 640},

    # FRA <-> ORD
    {"flight_number": "LS401", "airline": "LS", "origin": "FRA", "destination": "ORD", "departure_time": "06:00", "duration_hours": 9.5, "base_price": 700},
    {"flight_number": "LS403", "airline": "LS", "origin": "FRA", "destination": "ORD", "departure_time": "14:00", "duration_hours": 9.5, "base_price": 700},
    {"flight_number": "LS405", "airline": "LS", "origin": "FRA", "destination": "ORD", "departure_time": "22:00", "duration_hours": 9.5, "base_price": 700},
    {"flight_number": "LS402", "airline": "LS", "origin": "ORD", "destination": "FRA", "departure_time": "06:00", "duration_hours": 8.5, "base_price": 720},
    {"flight_number": "LS404", "airline": "LS", "origin": "ORD", "destination": "FRA", "departure_time": "14:00", "duration_hours": 8.5, "base_price": 720},
    {"flight_number": "LS406", "airline": "LS", "origin": "ORD", "destination": "FRA", "departure_time": "22:00", "duration_hours": 8.5, "base_price": 720},

    # SFO <-> LHR
    {"flight_number": "UY801", "airline": "UY", "origin": "SFO", "destination": "LHR", "departure_time": "06:00", "duration_hours": 10.5, "base_price": 850},
    {"flight_number": "UY803", "airline": "UY", "origin": "SFO", "destination": "LHR", "departure_time": "14:00", "duration_hours": 10.5, "base_price": 850},
    {"flight_number": "UY805", "airline": "UY", "origin": "SFO", "destination": "LHR", "departure_time": "22:00", "duration_hours": 10.5, "base_price": 850},
    {"flight_number": "UY802", "airline": "UY", "origin": "LHR", "destination": "SFO", "departure_time": "06:00", "duration_hours": 11.0, "base_price": 880},
    {"flight_number": "UY804", "airline": "UY", "origin": "LHR", "destination": "SFO", "departure_time": "14:00", "duration_hours": 11.0, "base_price": 880},
    {"flight_number": "UY806", "airline": "UY", "origin": "LHR", "destination": "SFO", "departure_time": "22:00", "duration_hours": 11.0, "base_price": 880},

    # USA domestic
    # JFK <-> LAX
    {"flight_number": "AW201", "airline": "AW", "origin": "JFK", "destination": "LAX", "departure_time": "06:00", "duration_hours": 6.0, "base_price": 320},
    {"flight_number": "AW203", "airline": "AW", "origin": "JFK", "destination": "LAX", "departure_time": "14:00", "duration_hours": 6.0, "base_price": 320},
    {"flight_number": "AW205", "airline": "AW", "origin": "JFK", "destination": "LAX", "departure_time": "22:00", "duration_hours": 6.0, "base_price": 320},
    {"flight_number": "AW202", "airline": "AW", "origin": "LAX", "destination": "JFK", "departure_time": "06:00", "duration_hours": 5.5, "base_price": 340},
    {"flight_number": "AW204", "airline": "AW", "origin": "LAX", "destination": "JFK", "departure_time": "14:00", "duration_hours": 5.5, "base_price": 340},
    {"flight_number": "AW206", "airline": "AW", "origin": "LAX", "destination": "JFK", "departure_time": "22:00", "duration_hours": 5.5, "base_price": 340},

    # JFK <-> SFO
    {"flight_number": "HW301", "airline": "HW", "origin": "JFK", "destination": "SFO", "departure_time": "06:00", "duration_hours": 6.5, "base_price": 350},
    {"flight_number": "HW303", "airline": "HW", "origin": "JFK", "destination": "SFO", "departure_time": "14:00", "duration_hours": 6.5, "base_price": 350},
    {"flight_number": "HW305", "airline": "HW", "origin": "JFK", "destination": "SFO", "departure_time": "22:00", "duration_hours": 6.5, "base_price": 350},
    {"flight_number": "HW302", "airline": "HW", "origin": "SFO", "destination": "JFK", "departure_time": "06:00", "duration_hours": 5.5, "base_price": 360},
    {"flight_number": "HW304", "airline": "HW", "origin": "SFO", "destination": "JFK", "departure_time": "14:00", "duration_hours": 5.5, "base_price": 360},
    {"flight_number": "HW306", "airline": "HW", "origin": "SFO", "destination": "JFK", "departure_time": "22:00", "duration_hours": 5.5, "base_price": 360},

    # ORD <-> LAX
    {"flight_number": "UY501", "airline": "UY", "origin": "ORD", "destination": "LAX", "departure_time": "06:00", "duration_hours": 4.5, "base_price": 280},
    {"flight_number": "UY503", "airline": "UY", "origin": "ORD", "destination": "LAX", "departure_time": "14:00", "duration_hours": 4.5, "base_price": 280},
    {"flight_number": "UY505", "airline": "UY", "origin": "ORD", "destination": "LAX", "departure_time": "22:00", "duration_hours": 4.5, "base_price": 280},
    {"flight_number": "UY502", "airline": "UY", "origin": "LAX", "destination": "ORD", "departure_time": "06:00", "duration_hours": 4.0, "base_price": 290},
    {"flight_number": "UY504", "airline": "UY", "origin": "LAX", "destination": "ORD", "departure_time": "14:00", "duration_hours": 4.0, "base_price": 290},
    {"flight_number": "UY506", "airline": "UY", "origin": "LAX", "destination": "ORD", "departure_time": "22:00", "duration_hours": 4.0, "base_price": 290},

    # Europe intra
    # CDG <-> FCO
    {"flight_number": "FL101", "airline": "FL", "origin": "CDG", "destination": "FCO", "departure_time": "06:00", "duration_hours": 2.0, "base_price": 180},
    {"flight_number": "FL103", "airline": "FL", "origin": "CDG", "destination": "FCO", "departure_time": "14:00", "duration_hours": 2.0, "base_price": 180},
    {"flight_number": "FL105", "airline": "FL", "origin": "CDG", "destination": "FCO", "departure_time": "22:00", "duration_hours": 2.0, "base_price": 180},
    {"flight_number": "FL102", "airline": "FL", "origin": "FCO", "destination": "CDG", "departure_time": "06:00", "duration_hours": 2.0, "base_price": 180},
    {"flight_number": "FL104", "airline": "FL", "origin": "FCO", "destination": "CDG", "departure_time": "14:00", "duration_hours": 2.0, "base_price": 180},
    {"flight_number": "FL106", "airline": "FL", "origin": "FCO", "destination": "CDG", "departure_time": "22:00", "duration_hours": 2.0, "base_price": 180},

    # LHR <-> AMS
    {"flight_number": "BS201", "airline": "BS", "origin": "LHR", "destination": "AMS", "departure_time": "06:00", "duration_hours": 1.5, "base_price": 150},
    {"flight_number": "BS203", "airline": "BS", "origin": "LHR", "destination": "AMS", "departure_time": "14:00", "duration_hours": 1.5, "base_price": 150},
    {"flight_number": "BS205", "airline": "BS", "origin": "LHR", "destination": "AMS", "departure_time": "22:00", "duration_hours": 1.5, "base_price": 150},
    {"flight_number": "BS202", "airline": "BS", "origin": "AMS", "destination": "LHR", "departure_time": "06:00", "duration_hours": 1.5, "base_price": 150},
    {"flight_number": "BS204", "airline": "BS", "origin": "AMS", "destination": "LHR", "departure_time": "14:00", "duration_hours": 1.5, "base_price": 150},
    {"flight_number": "BS206", "airline": "BS", "origin": "AMS", "destination": "LHR", "departure_time": "22:00", "duration_hours": 1.5, "base_price": 150},

    # FRA <-> BCN
    {"flight_number": "LS201", "airline": "LS", "origin": "FRA", "destination": "BCN", "departure_time": "06:00", "duration_hours": 2.5, "base_price": 200},
    {"flight_number": "LS203", "airline": "LS", "origin": "FRA", "destination": "BCN", "departure_time": "14:00", "duration_hours": 2.5, "base_price": 200},
    {"flight_number": "LS205", "airline": "LS", "origin": "FRA", "destination": "BCN", "departure_time": "22:00", "duration_hours": 2.5, "base_price": 200},
    {"flight_number": "LS202", "airline": "LS", "origin": "BCN", "destination": "FRA", "departure_time": "06:00", "duration_hours": 2.5, "base_price": 200},
    {"flight_number": "LS204", "airline": "LS", "origin": "BCN", "destination": "FRA", "departure_time": "14:00", "duration_hours": 2.5, "base_price": 200},
    {"flight_number": "LS206", "airline": "LS", "origin": "BCN", "destination": "FRA", "departure_time": "22:00", "duration_hours": 2.5, "base_price": 200},

    # Middle East connections
    # DXB <-> LHR
    {"flight_number": "DF201", "airline": "DF", "origin": "DXB", "destination": "LHR", "departure_time": "06:00", "duration_hours": 7.5, "base_price": 550},
    {"flight_number": "DF203", "airline": "DF", "origin": "DXB", "destination": "LHR", "departure_time": "14:00", "duration_hours": 7.5, "base_price": 550},
    {"flight_number": "DF205", "airline": "DF", "origin": "DXB", "destination": "LHR", "departure_time": "22:00", "duration_hours": 7.5, "base_price": 550},
    {"flight_number": "DF202", "airline": "DF", "origin": "LHR", "destination": "DXB", "departure_time": "06:00", "duration_hours": 7.0, "base_price": 580},
    {"flight_number": "DF204", "airline": "DF", "origin": "LHR", "destination": "DXB", "departure_time": "14:00", "duration_hours": 7.0, "base_price": 580},
    {"flight_number": "DF206", "airline": "DF", "origin": "LHR", "destination": "DXB", "departure_time": "22:00", "duration_hours": 7.0, "base_price": 580},

    # DXB <-> JFK
    {"flight_number": "DF301", "airline": "DF", "origin": "DXB", "destination": "JFK", "departure_time": "06:00", "duration_hours": 14.0, "base_price": 900},
    {"flight_number": "DF303", "airline": "DF", "origin": "DXB", "destination": "JFK", "departure_time": "14:00", "duration_hours": 14.0, "base_price": 900},
    {"flight_number": "DF305", "airline": "DF", "origin": "DXB", "destination": "JFK", "departure_time": "22:00", "duration_hours": 14.0, "base_price": 900},
    {"flight_number": "DF302", "airline": "DF", "origin": "JFK", "destination": "DXB", "departure_time": "06:00", "duration_hours": 12.5, "base_price": 920},
    {"flight_number": "DF304", "airline": "DF", "origin": "JFK", "destination": "DXB", "departure_time": "14:00", "duration_hours": 12.5, "base_price": 920},
    {"flight_number": "DF306", "airline": "DF", "origin": "JFK", "destination": "DXB", "departure_time": "22:00", "duration_hours": 12.5, "base_price": 920},

    # DOH <-> CDG
    {"flight_number": "PS101", "airline": "PS", "origin": "DOH", "destination": "CDG", "departure_time": "06:00", "duration_hours": 7.0, "base_price": 520},
    {"flight_number": "PS103", "airline": "PS", "origin": "DOH", "destination": "CDG", "departure_time": "14:00", "duration_hours": 7.0, "base_price": 520},
    {"flight_number": "PS105", "airline": "PS", "origin": "DOH", "destination": "CDG", "departure_time": "22:00", "duration_hours": 7.0, "base_price": 520},
    {"flight_number": "PS102", "airline": "PS", "origin": "CDG", "destination": "DOH", "departure_time": "06:00", "duration_hours": 6.5, "base_price": 540},
    {"flight_number": "PS104", "airline": "PS", "origin": "CDG", "destination": "DOH", "departure_time": "14:00", "duration_hours": 6.5, "base_price": 540},
    {"flight_number": "PS106", "airline": "PS", "origin": "CDG", "destination": "DOH", "departure_time": "22:00", "duration_hours": 6.5, "base_price": 540},

    # Asia connections
    # SIN <-> LHR
    {"flight_number": "MD401", "airline": "MD", "origin": "SIN", "destination": "LHR", "departure_time": "06:00", "duration_hours": 13.5, "base_price": 850},
    {"flight_number": "MD403", "airline": "MD", "origin": "SIN", "destination": "LHR", "departure_time": "14:00", "duration_hours": 13.5, "base_price": 850},
    {"flight_number": "MD405", "airline": "MD", "origin": "SIN", "destination": "LHR", "departure_time": "22:00", "duration_hours": 13.5, "base_price": 850},
    {"flight_number": "MD402", "airline": "MD", "origin": "LHR", "destination": "SIN", "departure_time": "06:00", "duration_hours": 13.0, "base_price": 870},
    {"flight_number": "MD404", "airline": "MD", "origin": "LHR", "destination": "SIN", "departure_time": "14:00", "duration_hours": 13.0, "base_price": 870},
    {"flight_number": "MD406", "airline": "MD", "origin": "LHR", "destination": "SIN", "departure_time": "22:00", "duration_hours": 13.0, "base_price": 870},

    # SIN <-> SFO
    {"flight_number": "MD501", "airline": "MD", "origin": "SIN", "destination": "SFO", "departure_time": "06:00", "duration_hours": 16.0, "base_price": 950},
    {"flight_number": "MD503", "airline": "MD", "origin": "SIN", "destination": "SFO", "departure_time": "14:00", "duration_hours": 16.0, "base_price": 950},
    {"flight_number": "MD505", "airline": "MD", "origin": "SIN", "destination": "SFO", "departure_time": "22:00", "duration_hours": 16.0, "base_price": 950},
    {"flight_number": "MD502", "airline": "MD", "origin": "SFO", "destination": "SIN", "departure_time": "06:00", "duration_hours": 15.5, "base_price": 980},
    {"flight_number": "MD504", "airline": "MD", "origin": "SFO", "destination": "SIN", "departure_time": "14:00", "duration_hours": 15.5, "base_price": 980},
    {"flight_number": "MD506", "airline": "MD", "origin": "SFO", "destination": "SIN", "departure_time": "22:00", "duration_hours": 15.5, "base_price": 980},

    # NRT <-> LAX
    {"flight_number": "SK701", "airline": "SK", "origin": "NRT", "destination": "LAX", "departure_time": "06:00", "duration_hours": 10.0, "base_price": 750},
    {"flight_number": "SK703", "airline": "SK", "origin": "NRT", "destination": "LAX", "departure_time": "14:00", "duration_hours": 10.0, "base_price": 750},
    {"flight_number": "SK705", "airline": "SK", "origin": "NRT", "destination": "LAX", "departure_time": "22:00", "duration_hours": 10.0, "base_price": 750},
    {"flight_number": "SK702", "airline": "SK", "origin": "LAX", "destination": "NRT", "departure_time": "06:00", "duration_hours": 11.5, "base_price": 780},
    {"flight_number": "SK704", "airline": "SK", "origin": "LAX", "destination": "NRT", "departure_time": "14:00", "duration_hours": 11.5, "base_price": 780},
    {"flight_number": "SK706", "airline": "SK", "origin": "LAX", "destination": "NRT", "departure_time": "22:00", "duration_hours": 11.5, "base_price": 780},

    # HND <-> SFO
    {"flight_number": "SK801", "airline": "SK", "origin": "HND", "destination": "SFO", "departure_time": "06:00", "duration_hours": 9.5, "base_price": 720},
    {"flight_number": "SK803", "airline": "SK", "origin": "HND", "destination": "SFO", "departure_time": "14:00", "duration_hours": 9.5, "base_price": 720},
    {"flight_number": "SK805", "airline": "SK", "origin": "HND", "destination": "SFO", "departure_time": "22:00", "duration_hours": 9.5, "base_price": 720},
    {"flight_number": "SK802", "airline": "SK", "origin": "SFO", "destination": "HND", "departure_time": "06:00", "duration_hours": 11.0, "base_price": 740},
    {"flight_number": "SK804", "airline": "SK", "origin": "SFO", "destination": "HND", "departure_time": "14:00", "duration_hours": 11.0, "base_price": 740},
    {"flight_number": "SK806", "airline": "SK", "origin": "SFO", "destination": "HND", "departure_time": "22:00", "duration_hours": 11.0, "base_price": 740},
]


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
