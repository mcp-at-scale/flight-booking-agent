"""
Tests for flight generation and querying.
"""

import pytest
from datetime import datetime
from chapter2.flights import (
    get_flight_for_date,
    get_flights_by_route,
    get_flight_by_number,
    get_all_flights_for_date,
    get_all_daily_flight_templates
)
from chapter2.models import Flight


def test_get_flight_for_date():
    """Test flight instance generation for a specific date."""
    templates = get_all_daily_flight_templates()
    template = templates[0]  # Get first template
    
    date = datetime(2025, 12, 15)
    flight = get_flight_for_date(template, date)
    
    assert isinstance(flight, Flight)
    assert flight.flight_number == template.flight_number
    assert flight.origin == template.origin
    assert flight.destination == template.destination
    assert flight.currency == "USD"
    assert 50 <= flight.available_seats <= 180


def test_get_flights_by_route():
    """Test getting all flights for a specific route."""
    date = datetime(2025, 12, 15)
    flights = get_flights_by_route("CDG", "JFK", date)
    
    assert len(flights) == 3  # Should have 3 flights per day
    assert all(flight.origin == "CDG" for flight in flights)
    assert all(flight.destination == "JFK" for flight in flights)
    assert all(isinstance(flight, Flight) for flight in flights)


def test_get_flights_by_nonexistent_route():
    """Test getting flights for a route that doesn't exist."""
    date = datetime(2025, 12, 15)
    flights = get_flights_by_route("CDG", "XXX", date)
    
    assert len(flights) == 0


def test_get_flight_by_number():
    """Test getting a specific flight by number."""
    date = datetime(2025, 12, 15)
    flight = get_flight_by_number("FL001", date)
    
    assert flight is not None
    assert flight.flight_number == "FL001"
    assert isinstance(flight, Flight)


def test_get_flight_by_invalid_number():
    """Test that invalid flight number returns None."""
    date = datetime(2025, 12, 15)
    flight = get_flight_by_number("XX999", date)
    
    assert flight is None


def test_get_all_flights_for_date():
    """Test getting all flights for a specific date."""
    date = datetime(2025, 12, 15)
    flights = get_all_flights_for_date(date)
    
    assert len(flights) > 100  # Should have 102 flights
    assert all(isinstance(flight, Flight) for flight in flights)


def test_flight_price_variation_weekend():
    """Test that weekend flights have price premiums."""
    templates = get_all_daily_flight_templates()
    template = templates[0]
    
    # Saturday (weekend)
    weekend_date = datetime(2025, 12, 20)  # Saturday
    weekend_flight = get_flight_for_date(template, weekend_date)
    
    # Monday (weekday)
    weekday_date = datetime(2025, 12, 15)  # Monday
    weekday_flight = get_flight_for_date(template, weekday_date)
    
    # Weekend should be more expensive (20% premium)
    assert weekend_flight.price > weekday_flight.price


def test_flight_deterministic_seats():
    """Test that seat availability is deterministic for same date."""
    date = datetime(2025, 12, 15)
    
    flight1 = get_flight_by_number("FL001", date)
    flight2 = get_flight_by_number("FL001", date)
    
    assert flight1.available_seats == flight2.available_seats
