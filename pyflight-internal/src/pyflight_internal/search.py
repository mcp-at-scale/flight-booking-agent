"""
Flight search functionality with support for direct flights and layovers.
All flights are considered daily operations.
"""

from datetime import datetime, timedelta
from typing import Union
from pyflight_internal.flights import get_flights_by_route, get_flight_for_date, get_all_daily_flight_templates
from pyflight_internal.airports import get_airport_by_code
from pyflight_internal.models import Flight, ConnectingFlight, SearchResult


def search_direct_flights(
    origin: str,
    destination: str,
    date: datetime
) -> list[Flight]:
    """
    Search for direct flights between two airports on a specific date.

    Args:
        origin: Origin airport code
        destination: Destination airport code
        date: Departure date

    Returns:
        List of direct flights
    """
    return get_flights_by_route(origin, destination, date)


def search_flights_with_one_layover(
    origin: str,
    destination: str,
    date: datetime,
    max_layover_hours: float = 6.0,
    min_layover_hours: float = 1.5
) -> list[ConnectingFlight]:
    """
    Search for flights with one layover between two airports.

    Args:
        origin: Origin airport code
        destination: Destination airport code
        date: Departure date
        max_layover_hours: Maximum layover duration in hours
        min_layover_hours: Minimum layover duration in hours

    Returns:
        List of connecting flights with one layover
    """
    # Find all possible layover airports (airports that have flights from origin)
    flight_templates = get_all_daily_flight_templates()
    layover_airports = set()
    for flight_template in flight_templates:
        if flight_template.origin == origin:
            layover_airports.add(flight_template.destination)

    # Remove destination if it's in layover airports (we want connecting flights, not direct)
    layover_airports.discard(destination)

    connecting_flights = []

    for layover_airport in layover_airports:
        # Get first leg flights
        first_flights = get_flights_by_route(origin, layover_airport, date)

        # Check if there are second leg flights from layover to destination
        second_leg_exists = any(
            f.origin == layover_airport and f.destination == destination
            for f in flight_templates
        )

        if not second_leg_exists:
            continue

        for first_flight in first_flights:
            first_arrival = datetime.fromisoformat(first_flight.arrival)

            # Try second legs on same day and next day
            for day_offset in [0, 1]:
                second_date = date + timedelta(days=day_offset)
                second_flights = get_flights_by_route(layover_airport, destination, second_date)

                for second_flight in second_flights:
                    second_departure = datetime.fromisoformat(second_flight.departure)

                    # Calculate layover duration
                    layover_duration = (second_departure - first_arrival).total_seconds() / 3600

                    # Check if layover is within acceptable range
                    if min_layover_hours <= layover_duration <= max_layover_hours:
                        # Calculate total duration and price
                        total_duration = (
                            first_flight.duration_hours +
                            layover_duration +
                            second_flight.duration_hours
                        )
                        total_price = first_flight.price + second_flight.price

                        # Check seat availability on both flights
                        min_seats = min(
                            first_flight.available_seats,
                            second_flight.available_seats
                        )
                        status = "scheduled" if min_seats > 0 else "sold_out"

                        connecting_flight = ConnectingFlight(
                            flight_number=f"{first_flight.flight_number}+{second_flight.flight_number}",
                            airline=f"{first_flight.airline}/{second_flight.airline}",
                            origin=origin,
                            destination=destination,
                            departure=first_flight.departure,
                            arrival=second_flight.arrival,
                            duration_hours=round(total_duration, 2),
                            price=round(total_price, 2),
                            currency="USD",
                            available_seats=min_seats,
                            total_seats=180,
                            status=status,
                            route_type="one_stop",
                            layover_airport=layover_airport,
                            layover_duration_hours=round(layover_duration, 2),
                            segments=[first_flight, second_flight]
                        )
                        connecting_flights.append(connecting_flight)

    return connecting_flights


def search_all_flights(
    origin: str,
    destination: str,
    date: datetime,
    max_layover_hours: float = 6.0,
    min_layover_hours: float = 1.5,
    include_connecting: bool = True
) -> SearchResult:
    """
    Search for all available flights (direct and with layovers).

    Args:
        origin: Origin airport code
        destination: Destination airport code
        date: Departure date
        max_layover_hours: Maximum layover duration in hours
        min_layover_hours: Minimum layover duration in hours
        include_connecting: Whether to include connecting flights

    Returns:
        SearchResult object with direct and connecting flights
    """
    # Validate airports
    origin_airport = get_airport_by_code(origin)
    destination_airport = get_airport_by_code(destination)

    if not origin_airport:
        raise ValueError(f"Unknown origin airport: {origin}")
    if not destination_airport:
        raise ValueError(f"Unknown destination airport: {destination}")
    if origin == destination:
        raise ValueError("Origin and destination cannot be the same")

    # Search for direct flights
    direct_flights = search_direct_flights(origin, destination, date)

    # Search for connecting flights if requested
    connecting_flights = []
    if include_connecting:
        connecting_flights = search_flights_with_one_layover(
            origin,
            destination,
            date,
            max_layover_hours,
            min_layover_hours
        )

    # Sort all flights by total duration
    all_flights = direct_flights + connecting_flights
    all_flights.sort(key=lambda x: (x.duration_hours, x.price))

    return SearchResult(
        origin=origin_airport,
        destination=destination_airport,
        date=date.strftime("%Y-%m-%d"),
        total_results=len(all_flights),
        direct_flights=len(direct_flights),
        connecting_flights=len(connecting_flights),
        flights=all_flights
    )


def format_flight_summary(flight: Union[Flight, ConnectingFlight]) -> str:
    """
    Format a flight as a human-readable summary.

    Args:
        flight: Flight or ConnectingFlight object

    Returns:
        Formatted string
    """
    departure = datetime.fromisoformat(flight.departure)
    arrival = datetime.fromisoformat(flight.arrival)

    summary = f"{flight.flight_number}: {flight.origin} → {flight.destination}\n"
    summary += f"  Departure: {departure.strftime('%Y-%m-%d %H:%M')}\n"
    summary += f"  Arrival: {arrival.strftime('%Y-%m-%d %H:%M')}\n"
    summary += f"  Duration: {flight.duration_hours:.1f}h\n"
    summary += f"  Price: ${flight.price:.2f}\n"
    summary += f"  Available seats: {flight.available_seats}\n"

    if isinstance(flight, ConnectingFlight):
        summary += f"  Layover: {flight.layover_airport} ({flight.layover_duration_hours:.1f}h)\n"

    return summary
