import json
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Callable, List
from uuid import uuid4

import requests
import xmltodict

from sythonlab_kiu_sdk.flights.dataclasses import FlightRequestMetadata, Itinerary, Passenger
from sythonlab_kiu_sdk.flights.enums import KiuTarget, Currency, FlightResultKind, RequestMethod

logger = logging.getLogger(__name__)


class KiuFlightSDK:
    debug: bool = False
    url_base: str = "https://ssl00.kiusys.com/ws3/index.php"
    username: Optional[str] = None
    password: Optional[str] = None
    headers: Dict[str, Any] = {}
    api_version = "3.0"
    target: Optional[KiuTarget] = None
    terminal_id: Optional[str] = None
    agent_sine: Optional[str] = None
    iso_country: Optional[str] = None
    iso_currency: Currency = Currency.USD

    def build_headers(self, headers: Optional[Dict[str, Any]] = None):
        if not headers:
            headers = {}

        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            **headers
        }

    def __init__(
            self,
            iso_country: Optional[str] = None,
            *,
            username: Optional[str] = None,
            password: Optional[str] = None,
            target: Optional[KiuTarget] = None,
            terminal_id: Optional[str] = None,
            agent_sine: Optional[str] = None,
            iso_currency: Optional[Currency] = Currency.USD,
            debug: Optional[bool] = False
    ):
        self.username = username or os.getenv("KIU_V3_USERNAME", None)
        self.password = password or os.getenv("KIU_V3_PASSWORD", None)
        self.target = target or KiuTarget(os.getenv("KIU_V3_TARGET", None))
        self.terminal_id = terminal_id or os.getenv("KIU_V3_TERMINAL_ID", None)
        self.agent_sine = agent_sine or os.getenv("KIU_V3_AGENT_SINE", None)
        self.iso_country = iso_country
        self.debug = debug if debug is not None else False
        if iso_currency:
            self.iso_currency = iso_currency

    def request(
            self,
            request_id: str,
            *,
            payload: Optional[Dict[str, Any]] = None,
            headers: Optional[Dict[str, Any]] = None,
            method: RequestMethod = RequestMethod.POST,
            response_as_json: bool = True,
            on_complete: Optional[Callable] = None,
            kind: Optional[FlightResultKind] = None,
            show_response: bool = False,
            timeout: Optional[int] = 100
    ):
        """Make an HTTP request to the specified URL with the given payload and headers."""

        if not payload:
            payload = {}

        self.build_headers(headers)

        as_xml = ""
        if payload:
            as_xml = xmltodict.unparse(payload)

        payload = f"user={self.username}&password={self.password}&request={as_xml}"

        start = datetime.now(timezone.utc)

        if self.debug:
            logger.debug("-" * 100)
            logger.debug("URL: %s", self.url_base)
            logger.debug("Start time: %s", start.strftime("%d/%m/%Y %H:%M:%S"))
            logger.debug("Headers: %s", headers)
            logger.debug("Payload: %s", payload)

        if method == RequestMethod.POST:
            response = requests.post(self.url_base, data=payload, headers=self.headers, timeout=timeout)
        else:
            raise ValueError("Unsupported request method")

        end = datetime.now(timezone.utc)

        if self.debug:
            logger.debug("-" * 100)
            logger.debug("End time: %s", end.strftime("%d/%m/%Y %H:%M:%S"))
            logger.debug("Duration: %s", end - start)
            logger.debug("Response status: %s", response.status_code)

        status_code, data = response.status_code, response.text

        if response_as_json:
            data = json.dumps(xmltodict.parse(data))

        if show_response:
            logger.debug("Response data: %s", data)

        if on_complete:
            on_complete(metadata=FlightRequestMetadata(
                status=status_code,
                request_id=request_id,
                kind=kind,
                headers=headers,
                request=payload,
                method=method,
                url=self.url_base,
                response=response.text,
                start_time=start,
                end_time=end,
                duration=(end - start).total_seconds() if end else None,
            ))

        if isinstance(data, dict):
            errors = self.extract_errors(data)
        else:
            errors = self.extract_errors(json.loads(data))

        if errors:
            return 400, errors

        return status_code, data

    @staticmethod
    def extract_errors(data: Dict[str, Any]):
        return data.get("Root", {}).get("Error")

    def check_connection(
            self,
            on_complete: Optional[Callable] = None,
            show_response: bool = False,
            timeout: Optional[int] = 100
    ):
        data = {
            "KIU_AirAvailRQ": {
                "@EchoToken": "1",
                "@TimeStamp": datetime.now(),
                "@Target": self.target.value,
                "@Version": self.api_version,
                "@SequenceNmbr": "1",
                "@PrimaryLangID": "en-us",
                "@DirectFlightsOnly": False,
                "@MaxResponses": 1,
                "@CombinedItineraries": False,
                "POS": {
                    "Source": {
                        "@AgentSine": self.agent_sine,
                        "@TerminalID": self.terminal_id,
                        "@ISOCountry": self.iso_country
                    }
                },
                "OriginDestinationInformation": [{
                    "DepartureDateTime": (datetime.today() + timedelta(days=10)).strftime("%Y-%m-%d"),
                    "OriginLocation": {
                        "@LocationCode": "KIN"
                    },
                    "DestinationLocation": {
                        "@LocationCode": "MIA"
                    }
                }],
                "TravelerInfoSummary": {
                    "AirTravelerAvail": {
                        "PassengerTypeQuantity": [
                            {"@Code": "ADT", "@Quantity": 1}
                        ]
                    }
                }
            }
        }

        return self.request(
            request_id=str(uuid4()),
            payload=data,
            on_complete=on_complete,
            show_response=show_response,
            timeout=timeout
        )

    def get_availability(
            self,
            itineraries: List[Itinerary],
            passengers: List[Passenger],
            *,
            direct_flights_only: Optional[bool] = False,
            max_stops_qty: Optional[int] = 4,
            on_complete: Optional[Callable] = None,
            show_response: bool = False,
            timeout: Optional[int] = 100
    ):
        """
            Documentation: https://kiuws-docs-agencies.kiusys.net/#eabefb5d-2cc2-4484-b4fb-3101bbb8fe3e
            Wiki: https://kiu.atlassian.net/wiki/spaces/KOD/pages/41025771/KIU+AirAvailRQ+RS

            Functionality:
            This method allows users to get the availability scheduled flights for an origin-destination in a certain date.
            KIU_AirAvailRQ allows also to get availability for more than one origin-destination list by date.
        """

        itinerary = [
            {
                "DepartureDateTime": item.departure_date,
                "OriginLocation": {
                    "@LocationCode": item.departing_from
                },
                "DestinationLocation": {
                    "@LocationCode": item.arriving_to
                }
            }
            for item in itineraries
        ]

        data = {
            "KIU_AirAvailRQ": {
                "@EchoToken": "1",
                "@TimeStamp": datetime.now(),
                "@Target": self.target.value,
                "@Version": self.api_version,
                "@SequenceNmbr": "1",
                "@PrimaryLangID": "en-us",
                "@DirectFlightsOnly": str(direct_flights_only).lower(),
                "@MaxResponses": "50",
                "@CombinedItineraries": "false",
                "POS": {
                    "Source": {
                        "@AgentSine": self.agent_sine,
                        "@TerminalID": self.terminal_id,
                        "@ISOCountry": self.iso_country
                    }
                },
                "OriginDestinationInformation": itinerary,
                "TravelPreferences": {
                    "@MaxStopsQuantity": (max_stops_qty, 0)[direct_flights_only is True],
                    "CabinPref": {
                        "@Cabin": "Economy"
                    }
                },
                "TravelerInfoSummary": {
                    "AirTravelerAvail": {
                        "PassengerTypeQuantity": [
                            {"@Code": item.kind.value, "@Quantity": item.qty}
                            for item in passengers
                        ]
                    }
                }
            }
        }

        return self.request(
            request_id=str(uuid4()),
            payload=data,
            on_complete=on_complete,
            show_response=show_response,
            timeout=timeout,
            kind=FlightResultKind.FLIGHT_SEARCH
        )

    # def pricing(self,
    #             *,
    #             outbound_departure_datetimes: str = None,
    #             outbound_arrival_datetimes: str = None,
    #             outbound_origin_location_codes: str = None,
    #             outbound_destination_location_codes: str = None,
    #             outbound_airline_codes: str = None,
    #             outbound_flight_numbers: str = None,
    #             outbound_rbd_codes: str = None,
    #             return_departure_datetimes: str = None,
    #             return_arrival_datetimes: str = None,
    #             return_origin_location_codes: str = None,
    #             return_destination_location_codes: str = None,
    #             return_airline_codes: str = None,
    #             return_flight_numbers: str = None,
    #             return_rbd_codes: str = None,
    #             passenger_qty: list = None,
    #             on_complete: Optional[Callable] = None,
    #             show_response: bool = False,
    #             timeout: Optional[int] = 100
    #             ):
    #     """
    #         Documentation: https://kiuws-docs-agencies.kiusys.net/#511cc2ef-2e0b-4498-91b6-a32d549b8544
    #         Wiki: https://kiu.atlassian.net/wiki/spaces/KOD/pages/41157010/KIU+AirPrice
    # 
    #         Functionality:
    #         This method offer to consumers two operation options:
    #         1 - Price itinerary without booked.
    #         2 - Re-price a reservation.
    #         Also users can reprice or price ancillaries booked in the reservation.
    # 
    #         Please see review the examples and the schemas associated.
    #     """
    # 
    #     outbound_flights = []
    #     return_flights = []
    # 
    #     for index in range(len(outbound_airline_codes)):
    #         outbound_flights.append({
    #             "@DepartureDateTime": outbound_departure_datetimes[index],
    #             "@ArrivalDateTime": outbound_arrival_datetimes[index],
    #             "@FlightNumber": outbound_flight_numbers[index],
    #             "@ResBookDesigCode": outbound_rbd_codes[index],
    #             "DepartureAirport": {
    #                 "@LocationCode": outbound_origin_location_codes[index]
    #             },
    #             "ArrivalAirport": {
    #                 "@LocationCode": outbound_destination_location_codes[index]
    #             },
    #             "MarketingAirline": {
    #                 "@Code": outbound_airline_codes[index]
    #             }
    #         })
    # 
    #     for index in range(len(return_airline_codes)):
    #         return_flights.append({
    #             "@DepartureDateTime": return_departure_datetimes[index],
    #             "@ArrivalDateTime": return_arrival_datetimes[index],
    #             "@FlightNumber": return_flight_numbers[index],
    #             "@ResBookDesigCode": return_rbd_codes[index],
    #             "DepartureAirport": {
    #                 "@LocationCode": return_origin_location_codes[index]
    #             },
    #             "ArrivalAirport": {
    #                 "@LocationCode": return_destination_location_codes[index]
    #             },
    #             "MarketingAirline": {
    #                 "@Code": return_airline_codes[index]
    #             }
    #         })
    # 
    #     options = [{'FlightSegment': outbound_flights}]
    # 
    #     if return_flights:
    #         options.append({'FlightSegment': return_flights})
    # 
    #     data = {
    #         'KIU_AirPriceRQ': {
    #             "@EchoToken": "WS3DOCEXAMPLE",
    #             "@TimeStamp": datetime.now(),
    #             '@Target': self.target,
    #             "@Version": "3.0",
    #             "@SequenceNmbr": "1",
    #             "@PrimaryLangID": "en-us",
    #             "POS": {
    #                 "Source": {
    #                     "@AgentSine": self.agent_sine,
    #                     "@TerminalID": self.terminal_id,
    #                     "@ISOCountry": self.iso_country,
    #                     "@ISOCurrency": self.iso_currency,
    #                     "RequestorID": {
    #                         "@Type": "5"
    #                     },
    #                     "BookingChannel": {
    #                         "@Type": "1"
    #                     }
    #                 }
    #             },
    #             "AirItinerary": {
    #                 "OriginDestinationOptions": {
    #                     "OriginDestinationOption": options
    #                 }
    #             },
    #             "TravelerInfoSummary": {
    #                 "PriceRequestInformation": None,
    #                 "AirTravelerAvail": {
    #                     "PassengerTypeQuantity": [
    #                         {'@Code': item['passenger_class'], '@Quantity': item['passenger_qty']}
    #                         for item in passenger_qty
    #                     ]
    #                 }
    #             }
    #         }
    #     }
    # 
    #     return self.request(
    #         request_id=str(uuid4()),
    #         payload=data,
    #         on_complete=on_complete,
    #         show_response=show_response,
    #         timeout=timeout,
    #         kind=FlightResultKind.FLIGHT_PRICING
    #     )
