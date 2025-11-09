"""
Tests for flight search functionality.
"""

import pytest
from datetime import datetime
from chapter2.search import (
    search_direct_flights,
    search_flights_with_one_layover,
    search_all_flights,
    format_flight_summary
)
from chapter2.models import Flight, ConnectingFlight, SearchResult


def test_search_direct_flights():
    """Test direct flight search."""
    date = datetime(2025, 12, 20)
    flights = search_direct_flights("CDG", "JFK", date)
    
    assert len(flights) == 3
    assert all(isinstance(flight, Flight) for flight in flights)
    assert all(flight.origin == "CDG" for flight in flights)
    assert all(flight.destination == "JFK" for flight in flights)


def test_search_direct_flights_no_results():
    """Test direct flight search with no results."""
    date = datetime(2025, 12, 20)
    flights = search_direct_flights("CDG", "NRT", date)
    
    assert len(flights) == 0


def test_search_flights_with_one_layover():
    """Test connecting flight search."""
    date = datetime(2025, 12, 20)
    flights = search_flights_with_one_layover("CDG", "LAX", date, max_layover_hours=24)
    
    assert len(flights) > 0
    assert all(isinstance(flight, ConnectingFlight) for flight in flights)
    assert all(flight.origin == "CDG" for flight in flights)
    assert all(flight.destination == "LAX" for flight in flights)
    assert all(hasattr(flight, 'layover_airport') for flight in flights)


def test_search_all_flights():
    """Test comprehensive flight search."""
    date = datetime(2025, 12, 20)
    result = search_all_flights("CDG", "JFK", date, include_connecting=False)
    
    assert isinstance(result, SearchResult)
    assert result.total_results == 3
    assert result.direct_flights == 3
    assert result.connecting_flights == 0
    assert result.origin.code == "CDG"
    assert result.destination.code == "JFK"


def test_search_all_flights_with_connecting():
    """Test search including connecting flights."""
    date = datetime(2025, 12, 20)
    result = search_all_flights("CDG", "LAX", date, include_connecting=True, max_layover_hours=24)
    
    assert isinstance(result, SearchResult)
    assert result.total_results > 0
    assert result.connecting_flights > 0


def test_search_invalid_origin():
    """Test search with invalid origin airport."""
    date = datetime(2025, 12, 20)
    
    with pytest.raises(ValueError, match="Unknown origin airport"):
        search_all_flights("XXX", "JFK", date)


def test_search_invalid_destination():
    """Test search with invalid destination airport."""
    date = datetime(2025, 12, 20)
    
    with pytest.raises(ValueError, match="Unknown destination airport"):
        search_all_flights("CDG", "XXX", date)


def test_search_same_origin_destination():
    """Test search with same origin and destination."""
    date = datetime(2025, 12, 20)
    
    with pytest.raises(ValueError, match="Origin and destination cannot be the same"):
        search_all_flights("CDG", "CDG", date)


def test_format_flight_summary_direct():
    """Test formatting direct flight summary."""
    date = datetime(2025, 12, 20)
    flights = search_direct_flights("CDG", "JFK", date)
    
    summary = format_flight_summary(flights[0])
    
    assert "CDG → JFK" in summary
    assert "Departure:" in summary
    assert "Arrival:" in summary
    assert "Price:" in summary
    assert "Available seats:" in summary


def test_format_flight_summary_connecting():
    """Test formatting connecting flight summary."""
    date = datetime(2025, 12, 20)
    flights = search_flights_with_one_layover("CDG", "LAX", date, max_layover_hours=24)
    
    if flights:
        summary = format_flight_summary(flights[0])
        
        assert "CDG → LAX" in summary
        assert "Layover:" in summary


def test_search_results_sorted_by_duration():
    """Test that search results are sorted by duration."""
    date = datetime(2025, 12, 20)
    result = search_all_flights("CDG", "LAX", date, include_connecting=True, max_layover_hours=24)
    
    # Check that flights are sorted by duration
    for i in range(len(result.flights) - 1):
        assert result.flights[i].duration_hours <= result.flights[i + 1].duration_hours
