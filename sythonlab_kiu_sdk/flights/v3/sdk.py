import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict, Any, Callable

import requests
import xmltodict

from sythonlab_kiu_sdk.flights.dataclasses import FlightRequestMetadata
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
    agent_since: Optional[str] = None
    iso_country: Optional[str] = None
    iso_currency: Currency = Currency.USD

    def __init__(
            self,
            iso_country: Optional[str] = None,
            *,
            username: Optional[str] = None,
            password: Optional[str] = None,
            target: Optional[KiuTarget] = None,
            terminal_id: Optional[str] = None,
            agent_since: Optional[str] = None,
            iso_currency: Optional[Currency] = None
    ):
        self.username = username or os.getenv("KIU_V3_USERNAME", None)
        self.password = password or os.getenv("KIU_V3_PASSWORD", None)
        self.target = target or KiuTarget(os.getenv("KIU_V3_TARGET", None))
        self.terminal_id = terminal_id or os.getenv("KIU_V3_TERMINAL_ID", None)
        self.agent_since = agent_since or os.getenv("KIU_V3_AGENT_SINCE", None)
        self.iso_country = iso_country

        if iso_currency:
            self.iso_currency = iso_currency

    def build_headers(self, headers: Optional[Dict[str, Any]] = None):
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            **headers
        }

    def request(
            self,
            request_id: str,
            *,
            url: str,
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
            logger.debug("URL: %s", url)
            logger.debug("Start time: %s", start.strftime("%d/%m/%Y %H:%M:%S"))
            logger.debug("Headers: %s", headers)
            logger.debug("Payload: %s", payload)

        if method == RequestMethod.POST:
            response = requests.post(url, data=payload, headers=headers, timeout=timeout)
        else:
            raise ValueError("Unsupported request method")

        end = None

        if self.debug:
            end = datetime.now(timezone.utc)

            logger.debug("-" * 100)
            logger.debug("End time: %s", end.strftime("%d/%m/%Y %H:%M:%S"))
            logger.debug("Duration: %s", end - start)
            logger.debug("Response status: %s", response.status_code)

            if show_response:
                try:
                    logger.debug("Response data: %s", response.json())
                except Exception:
                    logger.debug("Response raw data: %s", response.text)

        status_code, data = response.status_code, response.text

        if response_as_json:
            data = json.dumps(xmltodict.parse(data))

        if on_complete:
            on_complete(metadata=FlightRequestMetadata(
                status=status_code,
                request_id=request_id,
                kind=kind or FlightResultKind.UNKNOWN,
                headers=headers,
                request=payload,
                method=method,
                url=url,
                response=data,
                start_time=start,
                end_time=end,
                duration=(end - start).total_seconds() if end else None,
            ))

        return status_code, data
