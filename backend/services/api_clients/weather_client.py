"""
Open-Meteo API client — severe weather detection at Indian logistics hubs.
Completely free, no API key required.
Docs: https://open-meteo.com/en/docs
"""
from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Major Indian logistics hubs to monitor
MONITORING_HUBS = [
    {"name": "Chennai",            "lat": 13.0827, "lon": 80.2707},
    {"name": "Mumbai (JNPT)",      "lat": 18.9498, "lon": 72.9508},
    {"name": "Kolkata",            "lat": 22.5726, "lon": 88.3639},
    {"name": "Delhi NCR",          "lat": 28.6139, "lon": 77.2090},
    {"name": "Bangalore",          "lat": 12.9716, "lon": 77.5946},
    {"name": "Visakhapatnam",      "lat": 17.6868, "lon": 83.2185},
]

_BASE_PARAMS = {
    "hourly": "precipitation,windspeed_10m,wind_gusts_10m,precipitation_probability",
    "forecast_days": "1",
    "timezone": "Asia/Kolkata",
}


async def fetch_weather_signals() -> list[dict]:
    """
    Query Open-Meteo for severe weather at each hub.
    Returns raw_signal dicts for hubs with significant weather events.
    """
    signals: list[dict] = []
    async with httpx.AsyncClient(timeout=12.0) as client:
        for hub in MONITORING_HUBS:
            try:
                params = {**_BASE_PARAMS, "latitude": hub["lat"], "longitude": hub["lon"]}
                resp = await client.get(OPEN_METEO_URL, params=params)
                resp.raise_for_status()
                hourly = resp.json().get("hourly", {})

                precip       = hourly.get("precipitation", [0.0])
                wind         = hourly.get("windspeed_10m", [0.0])
                gusts        = hourly.get("wind_gusts_10m", [0.0])
                precip_prob  = hourly.get("precipitation_probability", [0.0])

                # Look at the next 6 hours only
                max_precip  = max(precip[:6],      default=0.0)
                max_gusts   = max(gusts[:6],        default=0.0)
                max_prob    = max(precip_prob[:6],  default=0.0)

                # Thresholds: >10 mm rain, >70% probability, or >60 km/h gusts
                if max_precip < 10.0 and max_prob < 70 and max_gusts < 60:
                    continue

                if max_gusts > 80:
                    event_type = "cyclone"
                elif max_precip > 15:
                    event_type = "flooding"
                else:
                    event_type = "heavy_rain"

                severity = min(10, max(3, int(max_precip / 5 + max_gusts / 20)))
                text = (
                    f"Severe weather alert at {hub['name']}: "
                    f"{max_precip:.1f}mm precipitation expected, "
                    f"wind gusts up to {max_gusts:.0f} km/h. "
                    f"Highway and logistics disruption likely."
                )
                signals.append(
                    {
                        "source": "open_meteo",
                        "raw_text": text,
                        "location": hub["name"],
                        "lat": hub["lat"],
                        "lon": hub["lon"],
                        "event_type": event_type,
                        "severity": severity,
                    }
                )
                logger.info(f"Open-Meteo: weather alert at {hub['name']} — {event_type} sev={severity}")
            except Exception as exc:
                logger.warning(f"Open-Meteo failed for {hub['name']}: {exc}")

    logger.info(f"Open-Meteo: {len(signals)} weather signals generated")
    return signals
