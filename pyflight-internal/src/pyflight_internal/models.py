"""
Pydantic models for the flight booking system.
"""

from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel, Field, ConfigDict


class Airline(BaseModel):
    """Model for airline information."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(..., description="Two-letter airline code")
    name: str = Field(..., description="Full airline name")
    country: str = Field(..., description="Country of origin")
    fleet_size: int = Field(..., ge=0, description="Number of aircraft in fleet")


class Airport(BaseModel):
    """Model for airport information."""

    model_config = ConfigDict(frozen=True)

    code: str = Field(..., description="Three-letter IATA airport code")
    name: str = Field(..., description="Full airport name")
    city: str = Field(..., description="City where airport is located")
    country: str = Field(..., description="Country where airport is located")
    timezone: str = Field(..., description="IANA timezone identifier")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")


class SeatSection(BaseModel):
    """Model for a seat section within an aircraft."""

    model_config = ConfigDict(frozen=True)

    rows: list[int] = Field(..., description="Row numbers in this section")
    columns: list[str] = Field(..., description="Column letters (e.g., A, B, C)")
    total: int = Field(..., ge=0, description="Total seats in this section")
    price_multiplier: float = Field(..., gt=0, description="Price multiplier relative to economy")


class Aircraft(BaseModel):
    """Model for an aircraft type with seat layout."""

    model_config = ConfigDict(frozen=True)

    model: str = Field(..., description="Aircraft model name")
    manufacturer: str = Field(..., description="Aircraft manufacturer")
    range_category: str = Field(..., pattern=r"^(short_haul|medium_haul|long_haul)$", description="Range category")
    max_range_km: int = Field(..., gt=0, description="Maximum range in kilometers")
    seats: dict[str, SeatSection] = Field(..., description="Seat sections by category (business, premium, economy)")
    total_seats: int = Field(..., gt=0, description="Total number of seats")

    def get_seat_category(self, seat: str) -> Optional[str]:
        """Return the category (business/premium/economy) for a given seat like '12A'."""
        row = int("".join(c for c in seat if c.isdigit()))
        col = "".join(c for c in seat if c.isalpha())
        for category, section in self.seats.items():
            if row in section.rows and col in section.columns:
                return category
        return None

    def list_seats(self, category: Optional[str] = None) -> list[str]:
        """List all seat numbers, optionally filtered by category."""
        seats = []
        for cat, section in self.seats.items():
            if category and cat != category:
                continue
            for row in section.rows:
                for col in section.columns:
                    seats.append(f"{row}{col}")
        return seats


class FlightTemplate(BaseModel):
    """Model for a daily flight template."""

    model_config = ConfigDict(frozen=True)

    flight_number: str = Field(..., description="Unique flight number")
    airline: str = Field(..., description="Airline code")
    origin: str = Field(..., description="Origin airport code")
    destination: str = Field(..., description="Destination airport code")
    departure_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="Departure time in HH:MM format")
    duration_hours: float = Field(..., gt=0, description="Flight duration in hours")
    base_price: float = Field(..., gt=0, description="Base price in USD")
    aircraft: str = Field(..., description="Aircraft model name")


class Flight(BaseModel):
    """Model for a flight instance on a specific date."""

    model_config = ConfigDict(frozen=False)

    flight_number: str = Field(..., description="Unique flight number")
    airline: str = Field(..., description="Airline code")
    origin: str = Field(..., description="Origin airport code")
    destination: str = Field(..., description="Destination airport code")
    departure: str = Field(..., description="Departure datetime in ISO format")
    arrival: str = Field(..., description="Arrival datetime in ISO format")
    duration_hours: float = Field(..., gt=0, description="Flight duration in hours")
    aircraft: str = Field(..., description="Aircraft model name")
    price: float = Field(..., gt=0, description="Flight price in USD")
    currency: str = Field(default="USD", description="Currency code")
    available_seats: int = Field(..., ge=0, description="Number of available seats")
    total_seats: int = Field(..., ge=0, description="Total seats on aircraft")
    status: str = Field(..., pattern=r"^(scheduled|sold_out|cancelled|delayed)$", description="Flight status")


class ConnectingFlight(BaseModel):
    """Model for a connecting flight with layover."""

    model_config = ConfigDict(frozen=False)

    flight_number: str = Field(..., description="Combined flight numbers (e.g., FL001+BS101)")
    airline: str = Field(..., description="Combined airline codes")
    origin: str = Field(..., description="Origin airport code")
    destination: str = Field(..., description="Destination airport code")
    departure: str = Field(..., description="First flight departure in ISO format")
    arrival: str = Field(..., description="Last flight arrival in ISO format")
    duration_hours: float = Field(..., gt=0, description="Total journey duration including layover")
    price: float = Field(..., gt=0, description="Total price for all segments")
    currency: str = Field(default="USD", description="Currency code")
    available_seats: int = Field(..., ge=0, description="Minimum available seats across all segments")
    total_seats: int = Field(default=180, description="Total seats")
    status: str = Field(..., description="Overall status")
    route_type: str = Field(default="one_stop", description="Type of route")
    layover_airport: str = Field(..., description="Airport code for layover")
    layover_duration_hours: float = Field(..., gt=0, description="Layover duration in hours")
    segments: list[Flight] = Field(..., min_length=2, description="Individual flight segments")


class SearchResult(BaseModel):
    """Model for flight search results."""

    model_config = ConfigDict(frozen=False)

    origin: Airport = Field(..., description="Origin airport information")
    destination: Airport = Field(..., description="Destination airport information")
    date: str = Field(..., description="Search date in YYYY-MM-DD format")
    total_results: int = Field(..., ge=0, description="Total number of flights found")
    direct_flights: int = Field(..., ge=0, description="Number of direct flights")
    connecting_flights: int = Field(..., ge=0, description="Number of connecting flights")
    flights: list[Union[Flight, ConnectingFlight]] = Field(default_factory=list, description="List of all flights")
