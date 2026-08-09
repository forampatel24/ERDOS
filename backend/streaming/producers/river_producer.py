"""Publishes river level events from CWC gauge data (with simulated fallback)."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

import httpx

from backend.utils.logging import get_logger
from backend.utils.time import now_utc, to_iso

logger = get_logger("streaming.producers.river")

#: Canonical event ``type`` emitted by the river producer.
RIVER_EVENT_TYPE = "river_update"

#: Default gauge station served by the producer.
DEFAULT_STATION_ID = "CWC-KOCHI"

#: Default request timeout for the river API (seconds).
_REQUEST_TIMEOUT = 10.0

#: Keys probed for each field across known CWC-style payloads.
_LEVEL_KEYS = ("water_level", "level", "river_level")
_RISE_KEYS = ("rise_rate", "water_rise_rate", "rise")
_STATION_KEYS = ("station_id", "river_station_id", "gauge_id", "id")


class CwcRiverClient:
    """HTTP client for a Central Water Commission-style gauge endpoint.

    The exact CWC response shape varies by deployment, so :class:`parse` probes
    a set of documented key aliases and accepts an optional custom parser.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        station_id: str = DEFAULT_STATION_ID,
        timeout: float = _REQUEST_TIMEOUT,
        parser: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = None,
    ) -> None:
        """Configure the client.

        :param url: CWC river-level endpoint. Defaults to
            ``settings.cwc_river_api_url``.
        :param station_id: gauge identifier reported when the payload does not
            include one.
        :param timeout: HTTP request timeout in seconds.
        :param parser: optional custom response parser; defaults to
            :meth:`parse`.
        """
        if url is None:
            from backend.utils.settings import settings

            url = settings.cwc_river_api_url
        self.url: str = url
        self.station_id: str = station_id
        self.timeout: float = timeout
        self._parser: Optional[Callable[[Dict[str, Any]], Dict[str, Any]]] = parser

    def fetch(self) -> Dict[str, Any]:
        """Fetch one river gauge reading from the CWC-style endpoint.

        :raises RuntimeError: when the request fails or no Recognised level
            field is found in the response.
        """
        try:
            response = httpx.get(self.url, timeout=self.timeout, follow_redirects=True)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:  # noqa: BLE001 - translate into a single error
            raise RuntimeError(f"CWC river request failed: {exc}") from exc

        if not isinstance(data, dict):
            raise RuntimeError("CWC river response is not a JSON object")

        parser = self._parser or self.parse
        try:
            return parser(data)
        except (KeyError, ValueError, TypeError) as exc:
            raise RuntimeError(f"CWC river payload not recognised: {exc}") from exc

    def parse(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract a canonical reading dict from a raw CWC-style payload.

        Probes the known key aliases; raises :class:`ValueError` when a
        water-level value cannot be found.
        """
        station = next((data[k] for k in _STATION_KEYS if k in data), self.station_id)
        level = _first(data, _LEVEL_KEYS)
        if level is None:
            raise ValueError("no recognised water_level field in the payload")
        rise = _first(data, _RISE_KEYS)
        if rise is None:
            rise = 0.0
        return {
            "station_id": str(station),
            "water_level": float(level),
            "rise_rate": float(rise),
        }


class RiverProducer:
    """Produces ``river_update`` events from CWC gauge data or the simulator.

    The primary source is :class:`CwcRiverClient`; the producer falls back to a
    simulated river reading from the disaster simulation engine whenever the
    live gauge is unreachable or unparsable.
    """

    def __init__(
        self,
        engine: Any = None,
        station_id: str = DEFAULT_STATION_ID,
        client: Optional[CwcRiverClient] = None,
        fallback_to_simulator: bool = True,
    ) -> None:
        """Configure the producer.

        :param engine: optional :class:`SimulationEngine` providing simulated
            fallback readings.
        :param station_id: gauge id used when the raw payload omits one.
        :param client: optional custom river client; defaults to
            :class:`CwcRiverClient`.
        :param fallback_to_simulator: fall back to the engine on live failure.
        """
        self.engine: Any = engine
        self.client: CwcRiverClient = client or CwcRiverClient(station_id=station_id)
        self.fallback_to_simulator: bool = fallback_to_simulator

    def fetch_reading(self, engine: Any = None) -> Dict[str, Any]:
        """Return one river reading dict (live, or simulated on failure).

        :param engine: overrides the configured engine when supplied.
        :raises RuntimeError: when both the live gauge and the fallback fail.
        """
        try:
            payload = self.client.fetch()
            return {**payload, "source": "cwc", "timestamp": to_iso(now_utc())}
        except Exception as exc:  # noqa: BLE001 - captured for fallback logging
            logger.warning("river fetch failed ({}); using simulator fallback", exc)
            fallback = engine if engine is not None else self.engine
            if not self.fallback_to_simulator or fallback is None:
                raise RuntimeError(
                    "Live river unavailable and no simulator fallback configured"
                ) from exc
            simulated = fallback.next_river_update()
            payload = simulated.get("payload", simulated)
            payload["timestamp"] = to_iso(now_utc())
            return payload

    def publish(self, engine: Any = None) -> Dict[str, Any]:
        """Read and return the canonical ``river_update`` event dict."""
        payload = self.fetch_reading(engine=engine)
        return {"type": RIVER_EVENT_TYPE, "payload": payload}


def _first(data: Dict[str, Any], keys: tuple[str, ...]) -> Optional[Any]:
    """Return the first present value of any ``key`` in ``data`` (else None)."""
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


__all__ = ["CwcRiverClient", "RiverProducer", "RIVER_EVENT_TYPE"]