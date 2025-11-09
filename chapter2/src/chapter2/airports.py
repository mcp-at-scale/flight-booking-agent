"""
Airport data management for the flight booking system.
"""

import json
from pathlib import Path
from typing import Optional
from chapter2.models import Airport

# Load airports data
_DATA_DIR = Path(__file__).parent / "data"
_airports_cache: Optional[list[Airport]] = None


def _load_airports() -> list[Airport]:
    """Load airports from JSON file."""
    global _airports_cache
    if _airports_cache is None:
        with open(_DATA_DIR / "airports.json", "r") as f:
            data = json.load(f)
            _airports_cache = [Airport(**airport) for airport in data]
    return _airports_cache


def get_airport_by_code(code: str) -> Optional[Airport]:
    """
    Get airport information by IATA code.

    Args:
        code: Three-letter IATA airport code

    Returns:
        Airport object if found, None otherwise
    """
    airports = _load_airports()
    return next((airport for airport in airports if airport.code == code), None)


def get_airports_by_city(city: str) -> list[Airport]:
    """
    Get all airports in a specific city.

    Args:
        city: City name

    Returns:
        List of Airport objects in the specified city
    """
    airports = _load_airports()
    return [airport for airport in airports if airport.city.lower() == city.lower()]


def get_airports_by_country(country: str) -> list[Airport]:
    """
    Get all airports in a specific country.

    Args:
        country: Country name

    Returns:
        List of Airport objects in the specified country
    """
    airports = _load_airports()
    return [airport for airport in airports if airport.country.lower() == country.lower()]


def get_all_airports() -> list[Airport]:
    """
    Get all available airports.

    Returns:
        List of all Airport objects
    """
    return _load_airports().copy()
