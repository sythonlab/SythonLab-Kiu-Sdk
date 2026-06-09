import datetime

from sythonlab_kiu_sdk.flights.dataclasses import Itinerary, Passenger
from sythonlab_kiu_sdk.flights.enums import PassengerType
from sythonlab_kiu_sdk.flights.v3.sdk import KiuFlightSDK

sdk = KiuFlightSDK(
    iso_country="JM",
    debug=True
)

status, data = sdk.get_availability(
    itineraries=[
        Itinerary(departure_date=datetime.date(year=2026, month=6, day=18), departing_from="SCU", arriving_to="GEO"),
        Itinerary(departure_date=datetime.date(year=2026, month=7, day=28), departing_from="GEO", arriving_to="SCU"),
    ],
    passengers=[
        Passenger(kind=PassengerType.ADULT, qty=1),
        Passenger(kind=PassengerType.CHILD, qty=1)
    ]
)

print(status, data)
