"""
Aircraft data management for the flight booking system.
"""

import json
from pathlib import Path
from typing import Optional
from pyflight_internal.models import Aircraft

_DATA_DIR = Path(__file__).parent / "data"
_aircraft_cache: Optional[list[Aircraft]] = None


def _load_aircraft() -> list[Aircraft]:
    """Load aircraft from JSON file."""
    global _aircraft_cache
    if _aircraft_cache is None:
        with open(_DATA_DIR / "aircraft.json", "r") as f:
            data = json.load(f)
            _aircraft_cache = [Aircraft(**a) for a in data]
    return _aircraft_cache


def get_aircraft_by_model(model: str) -> Optional[Aircraft]:
    """Get aircraft by model name."""
    aircraft_list = _load_aircraft()
    return next((a for a in aircraft_list if a.model == model), None)


def get_all_aircraft() -> list[Aircraft]:
    """Get all available aircraft."""
    return _load_aircraft().copy()


def get_aircraft_for_duration(duration_hours: float) -> Aircraft:
    """Select the appropriate aircraft based on flight duration.

    - Short haul (< 4h): Zephyr Z200
    - Medium haul (4-10h): Stratos S500
    - Long haul (> 10h): Celestia C900
    """
    aircraft_list = _load_aircraft()
    if duration_hours < 4:
        category = "short_haul"
    elif duration_hours <= 10:
        category = "medium_haul"
    else:
        category = "long_haul"
    return next(a for a in aircraft_list if a.range_category == category)
