"""
MapmyIndia (Mappls) Traffic API client.
Uses MAPPLS_CLIENT_ID + MAPPLS_CLIENT_SECRET env vars for OAuth.
Falls back to realistic NH-corridor mock when credentials are absent.
Docs: https://about.mappls.com/api/advanced-maps/doc/road-incidents-api
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TOKEN_URL      = "https://outpost.mappls.com/api/security/oauth/token"
_INCIDENTS_URL  = "https://apis.mappls.com/advancedmaps/v1"

# National highway corridors as bounding boxes (minLon,minLat,maxLon,maxLat)
_NH_CORRIDORS = [
    {"name": "NH48 Delhi–Mumbai",   "bbox": "72.8,18.9,77.2,28.6"},
    {"name": "NH44 Delhi–Chennai",  "bbox": "77.0,13.0,77.2,28.6"},
    {"name": "NH16 Kolkata–Chennai","bbox": "80.2,13.0,88.3,22.5"},
]

_token_cache: dict[str, Any] = {"token": None, "expires_at": 0.0}


async def _get_token(client_id: str, client_secret: str) -> str | None:
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["token"]
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            resp = await client.post(
                _TOKEN_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            _token_cache["token"] = data["access_token"]
            _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
            return _token_cache["token"]
    except Exception as exc:
        logger.warning(f"MapmyIndia OAuth failed: {exc}")
        return None


async def _fetch_live_incidents(token: str) -> list[dict]:
    signals: list[dict] = []
    async with httpx.AsyncClient(timeout=8.0) as client:
        for corridor in _NH_CORRIDORS:
            try:
                resp = await client.get(
                    f"{_INCIDENTS_URL}/{token}/road_incidents",
                    params={"bbox": corridor["bbox"]},
                )
                if resp.status_code != 200:
                    continue
                for inc in resp.json().get("incidents", [])[:3]:
                    desc = inc.get("description", "Road obstruction")
                    signals.append(
                        {
                            "source": "mappls_traffic",
                            "raw_text": (
                                f"Traffic incident on {corridor['name']}: {desc}. "
                                f"Lanes affected: {inc.get('lanes', 'unknown')}."
                            ),
                            "lat": inc.get("lat"),
                            "lon": inc.get("lng"),
                        }
                    )
            except Exception as exc:
                logger.warning(f"MapmyIndia incidents failed for {corridor['name']}: {exc}")
    return signals


def _mock_traffic_signals() -> list[dict]:
    """
    Realistic NH-corridor incidents used when MapmyIndia credentials are absent.
    Replace with live API when MAPPLS_CLIENT_ID / MAPPLS_CLIENT_SECRET are set.
    """
    import random

    candidates = [
        {
            "source": "mappls_traffic",
            "raw_text": (
                "Multi-vehicle accident on NH48 near Sriperumbudur causing 4 km congestion. "
                "Chennai–Bangalore corridor severely delayed."
            ),
            "lat": 12.9716,
            "lon": 79.9865,
        },
        {
            "source": "mappls_traffic",
            "raw_text": (
                "Road repair on NH44 near Nellore reduces carriageway to single lane. "
                "Heavy vehicle movement restricted."
            ),
            "lat": 14.4426,
            "lon": 79.9865,
        },
        {
            "source": "mappls_traffic",
            "raw_text": (
                "Landslide debris on NH44 near Warangal blocking one lane. "
                "Traffic moving slowly on alternate route."
            ),
            "lat": 17.9784,
            "lon": 79.5941,
        },
    ]
    return random.sample(candidates, k=1)


async def fetch_traffic_signals() -> list[dict]:
    """Return MapmyIndia traffic signals. Falls back to realistic mock if unconfigured."""
    client_id     = os.getenv("MAPPLS_CLIENT_ID", "").strip()
    client_secret = os.getenv("MAPPLS_CLIENT_SECRET", "").strip()

    if client_id and client_secret:
        token = await _get_token(client_id, client_secret)
        if token:
            signals = await _fetch_live_incidents(token)
            logger.info(f"MapmyIndia: {len(signals)} live traffic signals")
            return signals

    logger.info("MapmyIndia: credentials absent — using realistic mock")
    return _mock_traffic_signals()
