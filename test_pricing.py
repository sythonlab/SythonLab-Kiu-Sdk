import datetime

from sythonlab_kiu_sdk.flights.dataclasses import Itinerary, Passenger, ItineraryTravel
from sythonlab_kiu_sdk.flights.enums import PassengerType
from sythonlab_kiu_sdk.flights.v3.sdk import KiuFlightSDK

sdk = KiuFlightSDK(
    iso_country="JM",
    debug=True
)

availability_status, availability_data = sdk.get_availability(
    itineraries=[
        Itinerary(departure_date=datetime.date(year=2026, month=6, day=18), departing_from="SCU", arriving_to="GEO"),
        Itinerary(departure_date=datetime.date(year=2026, month=7, day=28), departing_from="GEO", arriving_to="SCU"),
    ],
    passengers=[
        Passenger(kind=PassengerType.ADULT, qty=1)
    ],
)

if availability_status == 200:
    availability_response = availability_data.get("KIU_AirAvailRS", {}).get("OriginDestinationInformation", [])

    rph = 1

    travels = []
    for item in availability_response:
        travel = []

        segments = item.get("OriginDestinationOptions", {}).get("OriginDestinationOption", []).get("FlightSegment", [])

        for segment in segments:
            flight_classes = segment.get("BookingClassAvail", [])
            if type(flight_classes) is not list:
                flight_classes = [flight_classes]

            travel.append(
                ItineraryTravel(
                    departure_datetime=segment.get("@DepartureDateTime"),
                    arrival_datetime=segment.get("@ArrivalDateTime"),
                    flight_number=segment.get("@FlightNumber"),
                    flight_class="E",
                    origin=segment.get("DepartureAirport", {}).get("@LocationCode"),
                    destination=segment.get("ArrivalAirport", {}).get("@LocationCode"),
                    airline_iata=segment.get("MarketingAirline", {}).get("@CompanyShortName"),
                )
            )
            rph += 1

        travels.append(travel)

    pricing_status, pricing_data = sdk.pricing(
        itineraries=travels,
        passengers=[
            Passenger(kind=PassengerType.ADULT, qty=1)
        ]
    )
    print(travels)
    print(pricing_status, pricing_data)
