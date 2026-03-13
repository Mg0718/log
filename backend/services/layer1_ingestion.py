"""
Layer 1 — Signal Ingestion Orchestrator.

Aggregates raw disruption signals from four Layer 1 source families:
    1. News & Events  — GDELT GEO 2.0 + NewsAPI (NEWSAPI_KEY optional)
    2. Open-Meteo     — free weather forecast API, no key required
    3. MapmyIndia     — traffic incidents API (MAPPLS_CLIENT_ID / MAPPLS_CLIENT_SECRET)
    4. GoComet/Ports  — port congestion index    (GOCOMET_API_KEY)

All source families are called concurrently. Per Requirement 1:
  - Each source failure is logged and skipped (other sources continue).
  - Results are normalised into raw_signal dicts → forwarded to RAG processor.
  - Polling interval ≤ 5 minutes (enforced by simulation_loop in main.py).

Falls back to a minimal hardcoded signal set only when ALL sources fail.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

_SOURCE_TIMEOUT_SECONDS = 10.0
_SOURCE_MAX_RETRIES = 3
_SOURCE_BACKOFF_BASE_SECONDS = 0.4


# ─────────────────────────────────────────────────────────────────────────────
# Async orchestrator (used by the main simulation & signal-injection loops)
# ─────────────────────────────────────────────────────────────────────────────

async def fetch_all_signals() -> list[dict]:
    """
    Concurrently poll all Layer 1 sources and merge results.
    Returns a flat list of raw_signal dicts ready for the RAG processor.
    """
    from backend.services.api_clients.news_client    import fetch_news_signals
    from backend.services.api_clients.weather_client import fetch_weather_signals
    from backend.services.api_clients.traffic_client import fetch_traffic_signals
    from backend.services.api_clients.ports_client   import fetch_port_signals

    source_calls: list[tuple[str, Callable[[], Awaitable[list[dict]]]]] = [
        ("news_events", fetch_news_signals),
        ("open_meteo", fetch_weather_signals),
        ("mappls_traffic", fetch_traffic_signals),
        ("gocomet_port", fetch_port_signals),
    ]

    results = await asyncio.gather(
        *[_fetch_with_resilience(name, fetcher) for name, fetcher in source_calls]
    )

    signals: list[dict] = []
    for source, source_signals in results:
        logger.info(f"Layer 1 — {source}: {len(source_signals)} signals")
        signals.extend(source_signals)

    if not signals:
        logger.warning("Layer 1 — all sources failed; using hardcoded fallback signals")
        signals = _fallback_signals()
    else:
        signals = [_normalize_signal(sig) for sig in signals]

    logger.info(f"Layer 1 — total signals fetched: {len(signals)}")
    return signals


async def _fetch_with_resilience(
    source_name: str,
    fetcher: Callable[[], Awaitable[list[dict]]],
) -> tuple[str, list[dict]]:
    """Fetch one source with timeout, retries, and graceful degradation."""
    last_exc: Exception | None = None

    for attempt in range(1, _SOURCE_MAX_RETRIES + 1):
        try:
            result = await asyncio.wait_for(fetcher(), timeout=_SOURCE_TIMEOUT_SECONDS)
            if not isinstance(result, list):
                raise TypeError(f"Expected list from {source_name}, got {type(result).__name__}")
            return source_name, result
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Layer 1 — %s attempt %s/%s failed: %s",
                source_name,
                attempt,
                _SOURCE_MAX_RETRIES,
                exc,
            )
            if attempt < _SOURCE_MAX_RETRIES:
                await asyncio.sleep(_SOURCE_BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)))

    logger.warning("Layer 1 — %s unavailable after retries: %s", source_name, last_exc)
    return source_name, []


def _normalize_signal(signal: dict) -> dict:
    """Add stable metadata while preserving existing raw signal keys for Layer 2."""
    if not isinstance(signal, dict):
        return {
            "source": "unknown",
            "raw_text": str(signal),
            "ingest_event_id": f"sig-{uuid.uuid4().hex[:12]}",
            "ingest_ts": int(time.time()),
            "schema_version": "1.0",
        }

    normalized = dict(signal)
    normalized.setdefault("source", "unknown")
    normalized.setdefault("raw_text", "")
    normalized.setdefault("ingest_event_id", f"sig-{uuid.uuid4().hex[:12]}")
    normalized.setdefault("ingest_ts", int(time.time()))
    normalized.setdefault("schema_version", "1.0")
    return normalized


# ─────────────────────────────────────────────────────────────────────────────
# Sync shim — kept for backward-compatibility with synchronous callers
# ─────────────────────────────────────────────────────────────────────────────

def get_raw_signals() -> list[dict]:
    """
    Synchronous wrapper retained for backward compatibility.
    New code should use `await fetch_all_signals()` directly.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Inside an async context — caller should have used await fetch_all_signals()
            logger.warning("get_raw_signals() called inside async context; returning fallback")
            return _fallback_signals()
        return loop.run_until_complete(fetch_all_signals())
    except Exception as exc:
        logger.warning(f"get_raw_signals() failed: {exc}")
        return _fallback_signals()


def _fallback_signals() -> list[dict]:
    return [
        {
            "source": "fallback",
            "raw_text": (
                "Heavy rainfall causes severe flooding on NH48 near Chennai, traffic halted."
            ),
        },
        {
            "source": "fallback",
            "raw_text": (
                "Port congestion worsening at Jawaharlal Nehru Port, "
                "vessel berthing delayed and container movement slowed."
            ),
        },
        {
            "source": "fallback",
            "raw_text": (
                "Cyclone warning issued for Kolkata corridor with likely "
                "highway disruption in the next 8 hours."
            ),
        },
    ]
