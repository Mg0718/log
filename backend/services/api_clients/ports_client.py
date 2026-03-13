"""
Port congestion signal client.
Live mode: uses GOCOMET_API_KEY env var to call GoComet Port Intelligence API.
Demo mode: generates realistic congestion signals from real Indian port data
           based on GoComet-style Container Congestion Index (CCI) patterns.
GoComet API docs: https://developers.gocomet.com/port-congestion
"""
from __future__ import annotations

import logging
import os
import random

logger = logging.getLogger(__name__)

# Real Indian major ports with baseline congestion profiles
_INDIAN_PORTS = [
    {
        "name": "Jawaharlal Nehru Port (JNPT), Mumbai",
        "lat": 18.9498,
        "lon": 72.9508,
        "congestion_prob": 0.40,   # ~40% chance of a congestion event
        "base_severity": 6,
        "base_wait_hours": 36,
    },
    {
        "name": "Chennai Port",
        "lat": 13.0827,
        "lon": 80.2707,
        "congestion_prob": 0.30,
        "base_severity": 5,
        "base_wait_hours": 24,
    },
    {
        "name": "Kolkata Port (Haldia Dock Complex)",
        "lat": 22.0667,
        "lon": 88.0698,
        "congestion_prob": 0.25,
        "base_severity": 5,
        "base_wait_hours": 20,
    },
    {
        "name": "Visakhapatnam Port",
        "lat": 17.6868,
        "lon": 83.2185,
        "congestion_prob": 0.20,
        "base_severity": 4,
        "base_wait_hours": 18,
    },
    {
        "name": "Mundra Port, Gujarat",
        "lat": 22.8395,
        "lon": 69.7222,
        "congestion_prob": 0.35,
        "base_severity": 6,
        "base_wait_hours": 30,
    },
]


async def _fetch_gocomet_live(api_key: str) -> list[dict]:
    import httpx

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(
                "https://api.gocomet.com/v1/port-congestion",
                headers={"Authorization": f"Bearer {api_key}"},
                params={"region": "india"},
            )
            resp.raise_for_status()
            signals = []
            for port in resp.json().get("ports", []):
                cci = port.get("cci_index", 0)
                if cci > 70:
                    signals.append(
                        {
                            "source": "gocomet_port",
                            "raw_text": (
                                f"Port congestion at {port['name']}: "
                                f"Container Congestion Index {cci}%. "
                                f"Vessel berthing delayed by {port.get('avg_wait_hours', 24)} hours. "
                                f"Container movement and cargo handling severely slowed."
                            ),
                            "lat": port.get("lat"),
                            "lon": port.get("lon"),
                            "event_type": "port_congestion",
                            "severity": min(10, int(cci / 10)),
                        }
                    )
            logger.info(f"GoComet: {len(signals)} live port congestion signals")
            return signals
    except Exception as exc:
        logger.warning(f"GoComet API failed: {exc}. Using realistic port simulation.")
        return _generate_port_signals()


def _generate_port_signals() -> list[dict]:
    """
    Simulate realistic GoComet-style port congestion signals.
    Based on actual Indian port historic congestion patterns.
    """
    signals = []
    for port in _INDIAN_PORTS:
        if random.random() < port["congestion_prob"]:
            wait_hours = port["base_wait_hours"] + random.randint(-8, 24)
            severity   = min(10, port["base_severity"] + random.randint(-1, 2))
            cci        = min(99, 60 + severity * 4)
            signals.append(
                {
                    "source": "gocomet_port",
                    "raw_text": (
                        f"Port congestion worsening at {port['name']}. "
                        f"Container Congestion Index at {cci}%. "
                        f"Vessel berthing delayed approximately {wait_hours} hours. "
                        f"Container movement and cargo handling severely slowed."
                    ),
                    "lat": port["lat"],
                    "lon": port["lon"],
                    "event_type": "port_congestion",
                    "severity": severity,
                }
            )
    logger.info(f"Port simulation: {len(signals)} congestion signals")
    return signals


async def fetch_port_signals() -> list[dict]:
    """Return port congestion signals. Uses GoComet API if GOCOMET_API_KEY is set."""
    api_key = os.getenv("GOCOMET_API_KEY", "").strip()
    if api_key:
        return await _fetch_gocomet_live(api_key)
    return _generate_port_signals()
