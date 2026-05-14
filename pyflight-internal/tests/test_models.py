"""
Tests for Pydantic models.
"""

import pytest
from pydantic import ValidationError
from pyflight_internal.models import Airline, Airport, FlightTemplate, Flight, ConnectingFlight


def test_airline_model():
    """Test Airline model creation and validation."""
    airline = Airline(
        code="FL",
        name="AeroLumière",
        country="FR",
        fleet_size=220
    )
    
    assert airline.code == "FL"
    assert airline.name == "AeroLumière"
    assert airline.country == "FR"
    assert airline.fleet_size == 220


def test_airline_frozen():
    """Test that Airline model is frozen (immutable)."""
    airline = Airline(code="FL", name="AeroLumière", country="FR", fleet_size=220)
    
    with pytest.raises(ValidationError):
        airline.code = "XX"


def test_airline_missing_required_field():
    """Test that missing required fields raise validation error."""
    with pytest.raises(ValidationError):
        Airline(name="Test Airline", country="Test")


def test_airport_model():
    """Test Airport model creation and validation."""
    airport = Airport(
        code="CDG",
        name="Charles de Gaulle Airport",
        city="Paris",
        country="FR",
        timezone="Europe/Paris",
        latitude=49.0097,
        longitude=2.5479
    )
    
    assert airport.code == "CDG"
    assert airport.city == "Paris"
    assert airport.latitude == 49.0097


def test_airport_coordinate_validation():
    """Test that invalid coordinates are rejected."""
    with pytest.raises(ValidationError):
        Airport(
            code="TEST",
            name="Test Airport",
            city="Test",
            country="Test",
            timezone="UTC",
            latitude=100.0,  # Invalid: > 90
            longitude=0.0
        )


def test_flight_template_model():
    """Test FlightTemplate model creation and validation."""
    template = FlightTemplate(
        flight_number="FL001",
        airline="FL",
        origin="CDG",
        destination="JFK",
        departure_time="06:00",
        duration_hours=8.5,
        base_price=650.0
    )
    
    assert template.flight_number == "FL001"
    assert template.departure_time == "06:00"
    assert template.duration_hours == 8.5


def test_flight_template_time_format():
    """Test that invalid time format is rejected."""
    with pytest.raises(ValidationError):
        FlightTemplate(
            flight_number="FL001",
            airline="FL",
            origin="CDG",
            destination="JFK",
            departure_time="6:00",  # Invalid format (missing leading zero)
            duration_hours=8.5,
            base_price=650.0
        )


def test_flight_model():
    """Test Flight model creation."""
    flight = Flight(
        flight_number="FL001",
        airline="FL",
        origin="CDG",
        destination="JFK",
        departure="2025-12-20T06:00:00",
        arrival="2025-12-20T14:30:00",
        duration_hours=8.5,
        price=715.0,
        available_seats=166,
        status="scheduled"
    )
    
    assert flight.flight_number == "FL001"
    assert flight.price == 715.0
    assert flight.available_seats == 166


def test_flight_seat_validation():
    """Test that seat count validation works."""
    with pytest.raises(ValidationError):
        Flight(
            flight_number="FL001",
            airline="FL",
            origin="CDG",
            destination="JFK",
            departure="2025-12-20T06:00:00",
            arrival="2025-12-20T14:30:00",
            duration_hours=8.5,
            price=715.0,
            available_seats=200,  # Invalid: > 180
            status="scheduled"
        )


def test_connecting_flight_model():
    """Test ConnectingFlight model creation."""
    flight1 = Flight(
        flight_number="FL001",
        airline="FL",
        origin="CDG",
        destination="JFK",
        departure="2025-12-20T06:00:00",
        arrival="2025-12-20T14:30:00",
        duration_hours=8.5,
        price=715.0,
        available_seats=166,
        status="scheduled"
    )
    
    flight2 = Flight(
        flight_number="AW203",
        airline="AW",
        origin="JFK",
        destination="LAX",
        departure="2025-12-20T22:00:00",
        arrival="2025-12-21T04:00:00",
        duration_hours=6.0,
        price=384.0,
        available_seats=72,
        status="scheduled"
    )
    
    connecting = ConnectingFlight(
        flight_number="FL001+AW203",
        airline="FL/AW",
        origin="CDG",
        destination="LAX",
        departure="2025-12-20T06:00:00",
        arrival="2025-12-21T04:00:00",
        duration_hours=22.0,
        price=1099.0,
        available_seats=72,
        status="scheduled",
        layover_airport="JFK",
        layover_duration_hours=7.5,
        segments=[flight1, flight2]
    )
    
    assert connecting.flight_number == "FL001+AW203"
    assert connecting.layover_airport == "JFK"
    assert len(connecting.segments) == 2
