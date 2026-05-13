"""
Tests for data loading from JSON files.
"""

import pytest
from pyflight_internal.airlines import get_all_airlines, get_airline_by_code
from pyflight_internal.airports import get_all_airports, get_airport_by_code
from pyflight_internal.flights import get_all_daily_flight_templates


def test_load_airlines():
    """Test that airlines load correctly from JSON."""
    airlines = get_all_airlines()
    
    assert len(airlines) == 10
    assert all(hasattr(airline, 'code') for airline in airlines)
    assert all(hasattr(airline, 'name') for airline in airlines)


def test_get_airline_by_code():
    """Test airline lookup by code."""
    airline = get_airline_by_code("FL")
    
    assert airline is not None
    assert airline.code == "FL"
    assert airline.name == "AeroLumière"
    assert airline.country == "France"


def test_get_airline_by_invalid_code():
    """Test that invalid airline code returns None."""
    airline = get_airline_by_code("XX")
    assert airline is None


def test_load_airports():
    """Test that airports load correctly from JSON."""
    airports = get_all_airports()
    
    assert len(airports) == 15
    assert all(hasattr(airport, 'code') for airport in airports)
    assert all(hasattr(airport, 'name') for airport in airports)
    assert all(hasattr(airport, 'latitude') for airport in airports)


def test_get_airport_by_code():
    """Test airport lookup by code."""
    airport = get_airport_by_code("CDG")
    
    assert airport is not None
    assert airport.code == "CDG"
    assert airport.name == "Charles de Gaulle Airport"
    assert airport.city == "Paris"
    assert airport.country == "France"


def test_get_airport_by_invalid_code():
    """Test that invalid airport code returns None."""
    airport = get_airport_by_code("XXX")
    assert airport is None


def test_load_flight_templates():
    """Test that flight templates load correctly from JSON."""
    templates = get_all_daily_flight_templates()
    
    assert len(templates) > 100  # Should have 102 flights
    assert all(hasattr(template, 'flight_number') for template in templates)
    assert all(hasattr(template, 'origin') for template in templates)
    assert all(hasattr(template, 'destination') for template in templates)


def test_flight_template_structure():
    """Test that flight templates have correct structure."""
    templates = get_all_daily_flight_templates()
    
    # Get first template
    template = templates[0]
    
    assert hasattr(template, 'airline')
    assert hasattr(template, 'departure_time')
    assert hasattr(template, 'duration_hours')
    assert hasattr(template, 'base_price')
    
    # Check data types
    assert isinstance(template.duration_hours, float)
    assert isinstance(template.base_price, (int, float))
