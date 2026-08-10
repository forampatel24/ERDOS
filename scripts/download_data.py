"""Download real historical datasets for ERDOS training.

Fetches free, public sources and stores them under ``datasets/``:

- ``datasets/raw/``         : raw provider payloads (unchanged).
- ``datasets/processed/``   : cleaned, training-ready CSV features.

Primary source today is the Open-Meteo Historical Weather Archive (no API key).
River gauge (CWC) is attempted but is best-effort: if unreachable, training can
fall back to simulated river values via the ERDOS simulator.

All downloaded data is git-ignored (see ``.gitignore``), so the repository stays
small while large datasets live only on the local machine.

Example
-------
.. code-block:: bash

    python scripts/download_data.py --start 2018 --end 2024 --place Kochi
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #

DATASETS_ROOT = Path("datasets")
RAW_DIR = DATASETS_ROOT / "raw" / "weather"
PROCESSED_DIR = DATASETS_ROOT / "processed"
HISTORICAL_DIR = DATASETS_ROOT / "historical"

OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

#: Coordinates of representative Kerala locations (lat, lon, name, district).
DEFAULT_PLACES: List[Dict[str, Any]] = [
    {"name": "Kochi", "lat": 9.9312, "lon": 76.2673, "district": "Ernakulam"},
    {"name": "Kottayam", "lat": 9.5916, "lon": 76.5212, "district": "Kottayam"},
    {"name": "Thiruvananthapuram", "lat": 8.5241, "lon": 76.9366, "district": "Thiruvananthapuram"},
    {"name": "Kozhikode", "lat": 11.2588, "lon": 75.7804, "district": "Kozhikode"},
    {"name": "Idukki", "lat": 9.8469, "lon": 76.9500, "district": "Idukki"},
]

#: Daily weather variables requested from Open-Meteo.
DAILY_VARIABLES = (
    "precipitation_sum",
    "rain_sum",
    "temperature_2m_max",
    "temperature_2m_min",
    "relative_humidity_2m_mean",
)

#: Best-effort CWC river-level gauges (station_id, river, district, lat, lon).
CWC_GAUGES: List[Dict[str, Any]] = [
    {"station_id": "CWC-KOCHI", "river": "Periyar", "district": "Ernakulam", "lat": 9.9820, "lon": 76.2740},
]


def utcnow_iso() -> str:
    """Return current UTC time as a compact ISO string."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Fetch helpers
# --------------------------------------------------------------------------- #

def http_get_json(url: str, timeout: int = 60) -> Optional[Dict[str, Any]]:
    """GET ``url`` and return parsed JSON, or ``None`` on any failure."""
    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        print(f"[warn] request failed for {url}: {exc}")
        return None


def fetch_openmeteo_history(
    lat: float, lon: float, start: date, end: date
) -> Optional[Dict[str, Any]]:
    """Fetch daily historical weather from the Open-Meteo archive.

    Returns the raw ``daily`` block (``{time: [...], precipitation_sum: [...]}``)
    or ``None`` if the provider could not be reached.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": "Asia/Kolkata",
    }
    return http_get_json(OPEN_METEO_ARCHIVE_URL + _query(params))


def fetch_cwc_river_levels(station_id: str) -> Optional[List[Dict[str, Any]]]:
    """Best-effort fetch of CWC river gauge readings.

    The CWC public portal does not offer a stable machine-readable history API,
    so this method usually returns ``None`` (the simulator then supplies river
    readings). Keep the function so a stable endpoint can be wired later without
    changing callers.
    """
    print(f"[info] CWC river gauge '{station_id}': no stable public API; skipped.")
    return None


def _query(params: Dict[str, Any]) -> str:
    """Build a ``?a=b&c=d`` query string from the mapping."""
    return "?" + "&".join(f"{k}={v}" for k, v in params.items())


# --------------------------------------------------------------------------- #
# Persistence
# --------------------------------------------------------------------------- #

def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def write_daily_csv(rows: List[Dict[str, Any]], path: Path) -> None:
    """Write ``rows`` (dicts with a fixed key set) as a CSV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_manifest(sources: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "generated_at": utcnow_iso(),
        "provider": "Open-Meteo Historical Weather Archive + CWC (best-effort)",
        "license_note": "Open-Meteo: CC-BY 4.0 / open data. CWC: public government data.",
        "sources": sources,
    }


# --------------------------------------------------------------------------- #
# Main pipeline
# --------------------------------------------------------------------------- #

def run(start_year: int, end_year: int, places: List[Dict[str, Any]]) -> int:
    start = date(start_year, 1, 1)
    end = date(end_year, 12, 31)
    print(f"Fetching daily history {start} .. {end} for {len(places)} places")
    if end_year > 2026 or start_year < 1940:
        print("[error] Open-Meteo archive covers ~1940..2026; adjust --start/--end.")
        return 1

    sources: List[Dict[str, Any]] = []
    all_rows: List[Dict[str, Any]] = []

    for place in places:
        lat, lon = float(place["lat"]), float(place["lon"])
        payload = fetch_openmeteo_history(lat, lon, start, end)
        if payload is None:
            print(f"[warn] no data for {place['name']}")
            continue
        daily = payload.get("daily") or {}
        times = daily.get("time") or []
        raw_path = RAW_DIR / f"{place['name'].lower()}_{start_year}_{end_year}.json"
        RAW_DIR.mkdir(parents=True, exist_ok=True)
        write_json(raw_path, payload)
        print(f"[ok] {place['name']} -> raw {raw_path} ({len(times)} days)")

        for idx, day in enumerate(times):
            row: Dict[str, Any] = {
                "date": day,
                "place": place["name"],
                "district": place["district"],
                "lat": lat,
                "lon": lon,
                "year": int(day[:4]),
                "precipitation_sum": _num(daily.get("precipitation_sum"), idx),
                "rain_sum": _num(daily.get("rain_sum"), idx),
                "temperature_max_c": _num(daily.get("temperature_2m_max"), idx),
                "temperature_min_c": _num(daily.get("temperature_2m_min"), idx),
                "humidity_percent": _num(daily.get("relative_humidity_2m_mean"), idx),
            }
            all_rows.append(row)

        sources.append(
            {
                "type": "weather_history",
                "place": place["name"],
                "district": place["district"],
                "lat": lat,
                "lon": lon,
                "url": OPEN_METEO_ARCHIVE_URL + _query(
                    {
                        "latitude": lat,
                        "longitude": lon,
                        "start_date": start.isoformat(),
                        "end_date": end.isoformat(),
                        "daily": ",".join(DAILY_VARIABLES),
                        "timezone": "Asia/Kolkata",
                    }
                ),
            }
        )

    if not all_rows:
        print("[error] no weather rows were fetched; check network / endpoints.")
        return 1

    all_rows.sort(key=lambda r: (r["date"], r["place"]))
    processed_path = PROCESSED_DIR / "kerala_daily_weather.csv"
    write_daily_csv(all_rows, processed_path)
    print(f"[ok] cleaned -> {processed_path} ({len(all_rows)} rows)")

    # Best-effort CWC rivers (simulator supplies readings if this yields nothing).
    for gauge in CWC_GAUGES:
        readings = fetch_cwc_river_levels(gauge["station_id"])
        if readings:
            write_csv = HISTORICAL_DIR / "cwc_river_levels.csv"
            rows = [
                {
                    "station_id": gauge["station_id"],
                    "river": gauge["river"],
                    "district": gauge["district"],
                    **reading,
                }
                for reading in readings
            ]
            write_daily_csv(rows, write_csv)
            sources.append({"type": "river_history", **gauge, "rows": len(rows)})

    manifest_path = DATASETS_ROOT / "manifest.json"
    write_json(manifest_path, build_manifest(sources))
    print(f"[ok] manifest -> {manifest_path}")
    print(f"[done] finished with {len(sources)} sources.")
    return 0


def _num(series: Optional[List[Any]], idx: int) -> Optional[float]:
    """Return a float for ``series[idx]`` or ``None`` if missing/blank."""
    if not series or idx >= len(series):
        return None
    value = series[idx]
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=int, default=2018, help="Start year (e.g. 2018)")
    parser.add_argument("--end", type=int, default=2024, help="End year (inclusive)")
    parser.add_argument(
        "--places",
        type=str,
        default="Kochi",
        help="Comma-separated place names; supports: "
        + ", ".join(p["name"] for p in DEFAULT_PLACES),
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    names = {p.strip() for p in args.places.split(",") if p.strip()}
    places = [p for p in DEFAULT_PLACES if p["name"] in names]
    if not places:
        print("[error] no valid --places. Choices: " + ", ".join(p["name"] for p in DEFAULT_PLACES))
        return
    raise SystemExit(run(args.start, args.end, places))


if __name__ == "__main__":
    main()