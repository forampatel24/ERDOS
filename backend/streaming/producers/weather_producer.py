"""Publishes weather events from Open-Meteo (with simulated fallback)."""

from __future__ import annotations

from typing import Any, Dict, Optional

import httpx

from backend.utils.logging import get_logger
from backend.utils.time import now_utc, to_iso
from config.constants import DEFAULT_LATITUDE, DEFAULT_LONGITUDE

logger = get_logger("streaming.producers.weather")

#: Canonical event ``type`` emitted by the weather producer.
WEATHER_EVENT_TYPE = "weather_update"

#: Default request timeout for the weather API (seconds).
_REQUEST_TIMEOUT = 10.0


class OpenMeteoClient:
    """Thin HTTP client for the Open-Meteo forecast API.

    Fetches the ``current`` weather block for a fixed location and returns a
    dict of scalar readings: ``rainfall_mm`` (precipitation, mm/h), 
    ``temperature_c``, ``humidity_pct`` and ``wind_speed_kmh``.
    """

    def __init__(
        self,
        url: Optional[str] = None,
        latitude: float = DEFAULT_LATITUDE,
        longitude: float = DEFAULT_LONGITUDE,
        timeout: float = _REQUEST_TIMEOUT,
    ) -> None:
        """Configure the client.

        :param url: Open-Meteo endpoint. Defaults to
            ``settings.weather_api_url``.
        :param latitude: monitoring latitude (default Kochi, Kerala).
        :param longitude: monitoring longitude (default Kochi, Kerala).
        :param timeout: HTTP request timeout in seconds.
        """
        if url is None:
            from backend.utils.settings import settings

            url = settings.weather_api_url
        self.url: str = url
        self.latitude: float = latitude
        self.longitude: float = longitude
        self.timeout: float = timeout

    def fetch(self) -> Dict[str, Any]:
        """Fetch one current weather reading from Open-Meteo.

        :raises RuntimeError: when the request fails or the response does not
            contain a parseable ``current`` block.
        """
        params = {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "current": "temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m",
            "timezone": "auto",
        }
        try:
            response = httpx.get(
                self.url, params=params, timeout=self.timeout, follow_redirects=True
            )
            response.raise_for_status()
            data = response.json()
        except Exception as exc:  # noqa: BLE001 - translate into a single error
            raise RuntimeError(f"Open-Meteo request failed: {exc}") from exc

        current = data.get("current") if isinstance(data, dict) else None
        if not isinstance(current, dict) or "temperature_2m" not in current:
            raise RuntimeError("Open-Meteo response missing the 'current' block")

        return {
            "rainfall_mm": float(current.get("precipitation", 0.0)),
            "temperature_c": float(current["temperature_2m"]),
            "humidity_pct": float(current.get("relative_humidity_2m", 0.0)),
            "wind_speed_kmh": float(current.get("wind_speed_10m", 0.0)),
        }


class WeatherProducer:
    """Produces ``weather_update`` events from Open-Meteo or the simulator.

    The primary source is :class:`OpenMeteoClient`. When live retrieval fails
    (no network, bad payload) the producer falls back to a simulated scenario
    from the disaster simulation engine so the pipeline keeps flowing.
    """

    def __init__(
        self,
        engine: Any = None,
        client: Optional[OpenMeteoClient] = None,
        fallback_to_simulator: bool = True,
    ) -> None:
        """Configure the producer.

        :param engine: optional :class:`SimulationEngine` used to provide a
            simulated fallback reading when the live API is unavailable.
        :param client: optional custom weather client; defaults to
            :class:`OpenMeteoClient` for the default Kochi location.
        :param fallback_to_simulator: when True and the live fetch fails, fall
            back to the engine's simulated weather.
        """
        self.engine: Any = engine
        self.client: OpenMeteoClient = client or OpenMeteoClient()
        self.fallback_to_simulator: bool = fallback_to_simulator

    def fetch_reading(self, engine: Any = None) -> Dict[str, Any]:
        """Return one weather reading dict (live, or simulated on failure).

        :param engine: overrides the configured engine when supplied.
        :raises RuntimeError: when both the live API and the fallback fail.
        """
        try:
            payload = self.client.fetch()
            return {**payload, "source": "open-meteo", "timestamp": to_iso(now_utc())}
        except Exception as exc:  # noqa: BLE001 - captured for fallback logging
            logger.warning("weather fetch failed ({}); using simulator fallback", exc)
            fallback = engine if engine is not None else self.engine
            if not self.fallback_to_simulator or fallback is None:
                raise RuntimeError(
                    "Live weather unavailable and no simulator fallback configured"
                ) from exc
            simulated = fallback.next_weather_update()
            payload = simulated.get("payload", simulated)
            payload["timestamp"] = to_iso(now_utc())
            return payload

    def publish(self, engine: Any = None) -> Dict[str, Any]:
        """Fetch one reading and return the canonical ``weather_update`` event."""
        payload = self.fetch_reading(engine=engine)
        return {"type": WEATHER_EVENT_TYPE, "payload": payload}


__all__ = ["OpenMeteoClient", "WeatherProducer", "WEATHER_EVENT_TYPE"]