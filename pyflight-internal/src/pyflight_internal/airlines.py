"""
Airline data management for the flight booking system.
"""

import json
from pathlib import Path
from typing import Optional
from pyflight_internal.models import Airline

# Load airlines data
_DATA_DIR = Path(__file__).parent / "data"
_airlines_cache: Optional[list[Airline]] = None

# BEGIN - REF - _load_airlines
def _load_airlines() -> list[Airline]:
    """Load airlines from JSON file."""
    global _airlines_cache
    if _airlines_cache is None:
        with open(_DATA_DIR / "airlines.json", "r") as f:
            data = json.load(f)
            _airlines_cache = [Airline(**airline) for airline in data]
    return _airlines_cache
# END - REF - _load_airlines

def get_airline_by_code(code: str) -> Optional[Airline]:
    """
    Get airline information by airline code.

    Args:
        code: Two-letter airline code

    Returns:
        Airline object if found, None otherwise
    """
    airlines = _load_airlines()
    return next((airline for airline in airlines if airline.code == code), None)


def get_all_airlines() -> list[Airline]:
    """
    Get all available airlines.

    Returns:
        List of all Airline objects
    """
    return _load_airlines().copy()
