"""
Kafka-lite event stream using Redis XStream with asyncio.Queue fallback.

Architecture:
  Producers (API clients) → publish raw signal dicts
  Consumer (RAG processor) → consume_batch() → extract DisruptionObjects

Redis  : uses XADD/XREADGROUP for durable, ordered streaming (like Kafka).
Fallback: asyncio.Queue if Redis is unavailable (no extra infra needed for demo).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os

logger = logging.getLogger(__name__)

_STREAM_KEY     = "logistics:signals"
_GROUP_NAME     = "rag_processor"
_CONSUMER_NAME  = "worker_1"

try:
    import redis.asyncio as aioredis
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False


class EventStream:
    """
    Unified event stream for the LogosGotham signal pipeline.

    Usage:
        stream = EventStream()
        await stream.try_connect_redis()  # optional; degrades gracefully

        # Producer side (API clients)
        await stream.publish({"source": "gdelt_news", "raw_text": "..."})

        # Consumer side (RAG processor)
        batch = await stream.consume_batch(max_count=10)
    """

    def __init__(self) -> None:
        self._queue: asyncio.Queue[dict] = asyncio.Queue(maxsize=500)
        self._redis = None
        self._use_redis = False

    async def try_connect_redis(self) -> None:
        """Try to connect to Redis. Silently falls back to in-memory queue."""
        if not _HAS_REDIS:
            logger.info("EventStream: redis package absent — using asyncio.Queue")
            return
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        try:
            r = aioredis.from_url(redis_url, decode_responses=True)
            await r.ping()
            self._redis = r
            self._use_redis = True
            # Create consumer group (idempotent)
            try:
                await self._redis.xgroup_create(_STREAM_KEY, _GROUP_NAME, id="0", mkstream=True)
            except Exception:
                pass  # group already exists
            logger.info(f"EventStream: connected to Redis at {redis_url}")
        except Exception as exc:
            logger.info(f"EventStream: Redis unavailable ({exc}) — using asyncio.Queue")

    @property
    def backend(self) -> str:
        return "redis" if self._use_redis else "memory"

    async def publish(self, signal: dict) -> None:
        """Push a raw signal dict onto the stream."""
        if self._use_redis and self._redis:
            try:
                await self._redis.xadd(_STREAM_KEY, {"data": json.dumps(signal)})
                return
            except Exception as exc:
                logger.warning(f"EventStream Redis publish failed: {exc} — falling back")
        # In-memory fallback: evict oldest on overflow
        if self._queue.full():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
        self._queue.put_nowait(signal)

    async def consume_batch(self, max_count: int = 20) -> list[dict]:
        """Pull up to max_count signals from the stream (non-blocking)."""
        if self._use_redis and self._redis:
            try:
                entries = await self._redis.xreadgroup(
                    _GROUP_NAME,
                    _CONSUMER_NAME,
                    {_STREAM_KEY: ">"},
                    count=max_count,
                    block=50,   # ms
                )
                signals: list[dict] = []
                for _stream, messages in entries:
                    for msg_id, fields in messages:
                        try:
                            signals.append(json.loads(fields.get("data", "{}")))
                        except json.JSONDecodeError:
                            pass
                        await self._redis.xack(_STREAM_KEY, _GROUP_NAME, msg_id)
                return signals
            except Exception as exc:
                logger.warning(f"EventStream Redis consume failed: {exc}")

        # In-memory fallback
        signals = []
        for _ in range(max_count):
            try:
                signals.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return signals


# Module-level singleton shared across the app
event_stream = EventStream()
