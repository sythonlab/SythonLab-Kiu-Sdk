from enum import Enum


class KiuTarget(Enum):
    TESTING = "Testing"
    PRODUCTION = "Production"


class Currency(Enum):
    """Represents different currency codes."""

    USD = "USD"
    JMD = "JMD"


class FlightResultKind(Enum):
    """Enum for the kind of flight result."""

    FLIGHT_SEARCH = "FLIGHT_SEARCH"
    FLIGHT_PRICING = "FLIGHT_PRICING"


class RequestMethod(Enum):
    """Represents HTTP request methods."""

    POST = "POST"


class PassengerType(Enum):
    """Represents the passengers types."""

    ADULT = "ADT"
    CHILD = "CNN"
    INFANT = "INF"
