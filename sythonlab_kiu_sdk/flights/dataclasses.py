from dataclasses import dataclass
from datetime import datetime, date
from typing import Any, Optional

from sythonlab_kiu_sdk.flights.enums import RequestMethod, FlightResultKind, PassengerType


@dataclass
class FlightRequestMetadata:
    """Dataclass for flight request metadata."""

    status: int
    request_id: str
    method: RequestMethod
    url: str
    kind: FlightResultKind
    headers: Any
    request: Any
    response: Any
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None


@dataclass
class Itinerary:
    """Dataclass for flight itinerary."""

    departure_date: date
    departing_from: str
    arriving_to: str


@dataclass
class Passenger:
    """Dataclass for passenger."""

    kind: PassengerType
    qty: int
