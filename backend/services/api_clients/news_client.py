"""
GDELT GEO 2.0 API client — India logistics disruption news.
Completely free, no API key required.
GDELT docs: https://blog.gdeltproject.org/gdelt-geo-2-0-api-debuts/

Also supports NewsAPI when NEWSAPI_KEY is configured.
"""
from __future__ import annotations

import asyncio
import logging
import os

import httpx

logger = logging.getLogger(__name__)

GDELT_URL = "https://api.gdeltproject.org/api/v2/geo/geo"
NEWSAPI_URL = "https://newsapi.org/v2/everything"

# Query targets India logistics disruption vocabulary
_QUERY = (
    "india (flood OR cyclone OR highway OR port OR rail OR traffic OR landslide "
    "OR disruption OR closure OR congestion OR accident) language:English"
)
_NEWSAPI_QUERY = (
    "(india) AND (flood OR cyclone OR highway OR port OR rail OR traffic OR "
    "landslide OR disruption OR closure OR congestion OR accident)"
)


async def _fetch_gdelt_signals() -> list[dict]:
    """Fetch recent India logistics disruption articles from GDELT GEO 2.0."""
    params = {
        "query": _QUERY,
        "mode": "artlist",
        "maxrecords": "15",
        "format": "json",
    }
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(GDELT_URL, params=params)
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
            signals = []
            for article in articles[:12]:
                title = (article.get("title") or "").strip()
                if not title:
                    continue
                signals.append(
                    {
                        "source": "gdelt_news",
                        "raw_text": title,
                        "url": article.get("url", ""),
                        "published_at": article.get("seendate", ""),
                    }
                )
            logger.info(f"GDELT: fetched {len(signals)} news signals")
            return signals
    except Exception as exc:
        logger.warning(f"GDELT API unavailable: {exc}")
        return []


async def _fetch_newsapi_signals() -> list[dict]:
    """Fetch disruption news from NewsAPI when a key is configured."""
    api_key = os.getenv("NEWSAPI_KEY", "").strip()
    if not api_key:
        logger.info("NewsAPI: NEWSAPI_KEY not configured; skipping")
        return []

    params = {
        "q": _NEWSAPI_QUERY,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": "12",
    }
    headers = {"X-Api-Key": api_key}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(NEWSAPI_URL, params=params, headers=headers)
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
            signals = []
            for article in articles:
                title = (article.get("title") or "").strip()
                desc = (article.get("description") or "").strip()
                raw_text = title if not desc else f"{title} - {desc}"
                if not raw_text.strip(" -"):
                    continue
                signals.append(
                    {
                        "source": "newsapi",
                        "raw_text": raw_text,
                        "url": article.get("url", ""),
                        "published_at": article.get("publishedAt", ""),
                    }
                )
            logger.info(f"NewsAPI: fetched {len(signals)} news signals")
            return signals
    except Exception as exc:
        logger.warning(f"NewsAPI unavailable: {exc}")
        return []


async def fetch_news_signals() -> list[dict]:
    """
    Fetch and merge disruption news from GDELT and NewsAPI.
    Returns raw_signal dicts compatible with Layer 2 RAG extraction.
    """
    gdelt_signals, newsapi_signals = await asyncio.gather(
        _fetch_gdelt_signals(),
        _fetch_newsapi_signals(),
    )
    merged = gdelt_signals + newsapi_signals
    logger.info(
        "News events aggregate: total=%s (gdelt=%s, newsapi=%s)",
        len(merged),
        len(gdelt_signals),
        len(newsapi_signals),
    )
    return merged
