"""
Layer 2 — LlamaIndex RAG Signal Processor.

Architecture (mirrors the diagram):
  1. INDEX  : Reference corpus of known Indian logistics disruptions stored as
              LlamaIndex Documents, indexed with keyword/BM25 retrieval.
  2. RETRIEVE: Top-k most similar examples retrieved for each incoming raw signal.
  3. GENERATE: Groq LLM (llama-3-70b-8192) extracts a structured DisruptionObject
              from raw text augmented with the retrieved context (few-shot RAG).
  4. FALLBACK: Rule-based extractor when LLM / retriever is unavailable.

Output schema (DisruptionObject):
    {
        "type":        str,    # flooding | cyclone | port_congestion | highway_closure ...
        "location":    str,
        "lat":         float,
        "lon":         float,
        "severity":    int,    # 1–10
        "radius_km":   float,
        "text_summary": str,
        "source":      str,
    }
"""
from __future__ import annotations

import ast
import json
import logging
import os
import re
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Reference corpus — the RAG knowledge base
# Each entry represents a real Indian logistics disruption pattern.
# ─────────────────────────────────────────────────────────────────────────────
_CORPUS: list[dict] = [
    {
        "id": "flood_nh48_chennai",
        "text": "Heavy rainfall causes severe flooding on NH48 near Chennai, traffic halted.",
        "structured": {
            "type": "flooding", "location": "Chennai",
            "lat": 13.0827, "lon": 80.2707, "severity": 8, "radius_km": 35.0,
        },
    },
    {
        "id": "flood_nh44_nellore",
        "text": "Waterlogging on NH44 near Nellore due to intense monsoon rains. Trucks stranded.",
        "structured": {
            "type": "flooding", "location": "Nellore",
            "lat": 14.4426, "lon": 79.9865, "severity": 7, "radius_km": 30.0,
        },
    },
    {
        "id": "port_congestion_jnpt",
        "text": "Port congestion worsening at Jawaharlal Nehru Port, vessel berthing delayed and container movement slowed.",
        "structured": {
            "type": "port_congestion", "location": "JNPT Mumbai",
            "lat": 18.9498, "lon": 72.9508, "severity": 6, "radius_km": 18.0,
        },
    },
    {
        "id": "cyclone_kolkata",
        "text": "Cyclone warning issued for Kolkata corridor with likely highway disruption in the next 8 hours.",
        "structured": {
            "type": "cyclone", "location": "Kolkata",
            "lat": 22.5726, "lon": 88.3639, "severity": 9, "radius_km": 60.0,
        },
    },
    {
        "id": "port_congestion_chennai",
        "text": "Chennai Port: Container Congestion Index elevated to 85%. Vessel waiting time exceeds 48 hours.",
        "structured": {
            "type": "port_congestion", "location": "Chennai Port",
            "lat": 13.0827, "lon": 80.2707, "severity": 7, "radius_km": 15.0,
        },
    },
    {
        "id": "highway_accident_nh48",
        "text": "Multi-vehicle accident on NH48 near Sriperumbudur causing severe congestion. Road blocked.",
        "structured": {
            "type": "highway_closure", "location": "NH48 Sriperumbudur",
            "lat": 12.9716, "lon": 79.9865, "severity": 6, "radius_km": 10.0,
        },
    },
    {
        "id": "cyclone_visakha",
        "text": "Severe cyclonic storm approaching Visakhapatnam coast. Port operations suspended.",
        "structured": {
            "type": "cyclone", "location": "Visakhapatnam",
            "lat": 17.6868, "lon": 83.2185, "severity": 9, "radius_km": 75.0,
        },
    },
    {
        "id": "flood_kolkata_haldia",
        "text": "Heavy rains flood arterial roads in Kolkata. Haldia dock approach road submerged.",
        "structured": {
            "type": "flooding", "location": "Kolkata Haldia",
            "lat": 22.0667, "lon": 88.0698, "severity": 7, "radius_km": 40.0,
        },
    },
    {
        "id": "road_repair_nh44",
        "text": "Planned road repair on NH44 reduces traffic to single lane near Nellore. Heavy trucks diverted.",
        "structured": {
            "type": "highway_closure", "location": "NH44 Nellore",
            "lat": 14.4426, "lon": 79.9865, "severity": 4, "radius_km": 8.0,
        },
    },
    {
        "id": "fog_delhi",
        "text": "Dense fog on NH48 Delhi–Jaipur section reduces visibility to near zero. Highway patrol deployed.",
        "structured": {
            "type": "weather_hazard", "location": "Delhi NCR",
            "lat": 28.6139, "lon": 77.2090, "severity": 5, "radius_km": 50.0,
        },
    },
    {
        "id": "port_mundra",
        "text": "Mundra Port congestion index at 78%. Container dwell time up 40%. Ships anchored offshore.",
        "structured": {
            "type": "port_congestion", "location": "Mundra Port Gujarat",
            "lat": 22.8395, "lon": 69.7222, "severity": 7, "radius_km": 20.0,
        },
    },
    {
        "id": "landslide_nh44_warangal",
        "text": "Landslide on NH44 near Warangal blocks one lane. Traffic moving slowly on alternate route.",
        "structured": {
            "type": "highway_closure", "location": "NH44 Warangal",
            "lat": 17.9784, "lon": 79.5941, "severity": 5, "radius_km": 12.0,
        },
    },
    {
        "id": "cyclone_alert_mumbai",
        "text": "Deep depression in Arabian Sea likely to intensify into cyclone near Mumbai coast. "
                "Port operations on alert.",
        "structured": {
            "type": "cyclone", "location": "Mumbai Coast",
            "lat": 18.9498, "lon": 72.8777, "severity": 8, "radius_km": 80.0,
        },
    },
    {
        "id": "flood_guwahati",
        "text": "Brahmaputra river overflow floods National Highway in Guwahati. "
                "Northeast India logistics severely disrupted.",
        "structured": {
            "type": "flooding", "location": "Guwahati",
            "lat": 26.1445, "lon": 91.7362, "severity": 8, "radius_km": 45.0,
        },
    },
]

_CORPUS_BY_ID = {item["id"]: item for item in _CORPUS}


class LlamaIndexRAGProcessor:
    """
    LlamaIndex RAG pipeline for DisruptionObject extraction.

    Steps:
      1. Retrieve relevant corpus examples via keyword similarity (BM25 / overlap)
      2. Build augmented prompt with retrieved few-shot examples
      3. Call Groq LLM for structured JSON extraction
      4. Fall back to rule-based extraction on failure
    """

    def __init__(self) -> None:
        self._groq_key  = os.getenv("GROQ_API_KEY", "").strip()
        self._llm       = None
        self._documents = None
        self._retriever = None
        self._retrieval_backend = "keyword"
        self._initialized = False

    # ──────────────────────────────────────────────────────
    # Initialisation (lazy, called on first use)
    # ──────────────────────────────────────────────────────

    def _initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._build_index()
        if self._groq_key:
            self._build_llm()

    def _build_index(self) -> None:
        """Build LlamaIndex documents and retriever, with fallback to keyword retrieval."""
        try:
            from llama_index.core import Document

            self._documents = [
                Document(
                    text=item["text"],
                    metadata={"structured": json.dumps(item["structured"]), "id": item["id"]},
                    doc_id=item["id"],
                )
                for item in _CORPUS
            ]

            # Prefer BM25 retriever to match architecture; fallback is deterministic keyword overlap.
            self._retriever = None
            self._retrieval_backend = "keyword"
            try:
                from llama_index.core.node_parser import SentenceSplitter
                from llama_index.retrievers.bm25 import BM25Retriever

                splitter = SentenceSplitter(chunk_size=256, chunk_overlap=20)
                nodes = splitter.get_nodes_from_documents(self._documents)
                self._retriever = BM25Retriever.from_defaults(nodes=nodes, similarity_top_k=3)
                self._retrieval_backend = "llamaindex_bm25"
            except Exception as retriever_exc:
                logger.info(f"LlamaIndex BM25 unavailable; using keyword retrieval: {retriever_exc}")

            logger.info(
                "LlamaIndex RAG: indexed %s reference disruption documents (retriever=%s)",
                len(self._documents),
                self._retrieval_backend,
            )
        except Exception as exc:
            logger.warning(f"LlamaIndex Document build failed: {exc}. Keyword fallback only.")
            self._documents = None
            self._retriever = None
            self._retrieval_backend = "keyword"

    def _build_llm(self) -> None:
        """Initialise Groq LLM via llama-index-llms-groq."""
        try:
            from llama_index.llms.groq import Groq  # type: ignore

            self._llm = Groq(model="llama3-70b-8192", api_key=self._groq_key)
            logger.info("LlamaIndex RAG: Groq LLM (llama3-70b-8192) ready")
        except Exception as exc:
            logger.warning(f"LlamaIndex Groq LLM init failed: {exc}. Rule-based fallback only.")
            self._llm = None

    # ──────────────────────────────────────────────────────
    # Retrieval
    # ──────────────────────────────────────────────────────

    def _retrieve_similar(self, text: str, top_k: int = 3) -> list[dict]:
        """
        Retrieve top-k similar corpus entries via keyword overlap.
        Uses LlamaIndex Document metadata; falls back to plain word overlap.
        """
        if self._retriever is not None:
            try:
                results = self._retriever.retrieve(text)
                similar: list[dict] = []
                for item in results[:top_k]:
                    node = getattr(item, "node", item)
                    metadata = getattr(node, "metadata", {}) or {}

                    item_id = metadata.get("id")
                    if item_id and item_id in _CORPUS_BY_ID:
                        similar.append(_CORPUS_BY_ID[item_id])
                        continue

                    structured_raw = metadata.get("structured")
                    if not structured_raw:
                        continue
                    try:
                        structured = json.loads(structured_raw) if isinstance(structured_raw, str) else structured_raw
                    except Exception:
                        continue

                    node_text = (getattr(node, "text", "") or metadata.get("text") or "").strip()
                    if not node_text:
                        continue

                    similar.append(
                        {
                            "id": str(item_id or f"retrieved-{len(similar)}"),
                            "text": node_text,
                            "structured": structured,
                        }
                    )

                if similar:
                    return similar[:top_k]
            except Exception as exc:
                logger.debug(f"LlamaIndex retrieve failed; using keyword fallback: {exc}")

        lowered = set(text.lower().split())
        scored: list[tuple[int, dict]] = []
        for item in _CORPUS:
            corpus_words = set(item["text"].lower().split())
            score = len(lowered & corpus_words)
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]

    # ──────────────────────────────────────────────────────
    # Extraction
    # ──────────────────────────────────────────────────────

    def extract(self, raw_signal: dict[str, Any]) -> dict[str, Any] | None:
        """
        Convert a raw_signal dict into a structured DisruptionObject.
        Returns None if the signal cannot be meaningfully structured.
        """
        self._initialize()

        text = (raw_signal.get("raw_text") or "").strip()
        if not text:
            return None

        # 1. Retrieve similar examples from corpus (RAG step)
        similar = self._retrieve_similar(text)

        # 2. Try LLM extraction with retrieved few-shot context
        result: dict | None = None
        if self._llm:
            result = self._extract_with_llm(text, similar)

        # 3. Fall back to rule-based extraction using best retrieved example
        if result is None:
            result = self._extract_with_rules(text, similar, raw_signal)

        # 4. Enrich with explicit source coordinates if provided
        return self._enrich(result, raw_signal)

    def _extract_with_llm(self, text: str, similar: list[dict]) -> dict | None:
        """
        RAG-augmented structured extraction via Groq.
        Retrieved examples are injected as few-shot context into the prompt.
        """
        try:
            few_shot_block = "\n".join(
                f'Input: "{ex["text"]}"\nOutput: {json.dumps(ex["structured"])}'
                for ex in similar
            )
            prompt = (
                "You are a logistics disruption entity extractor for Indian supply chains.\n"
                "Extract a structured DisruptionObject from the input text.\n"
                "Return ONLY a single JSON object with these exact keys:\n"
                '  "type" (string), "location" (string), "lat" (number), '
                '"lon" (number), "severity" (integer 1-10), "radius_km" (number)\n'
                "No explanation. No markdown. Only the JSON object.\n\n"
                f"--- Reference examples (retrieved) ---\n{few_shot_block}\n\n"
                f'--- Now extract ---\nInput: "{text}"\nOutput:'
            )
            response = str(self._llm.complete(prompt))
            json_match = re.search(r"\{.*?\}", response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as exc:
            logger.debug(f"LlamaIndex RAG LLM extraction failed: {exc}")
        return None

    def _extract_with_rules(self, text: str, similar: list[dict], raw_signal: dict) -> dict:
        """
        Template-based extractor: uses best-matching corpus entry as template,
        overrides specific fields from raw_signal and text keywords.
        """
        result = dict(similar[0]["structured"]) if similar else {}

        # Keyword-based type override
        lowered = text.lower()
        if not result.get("type"):
            if "flood" in lowered or "waterlog" in lowered or "submerged" in lowered:
                result["type"] = "flooding"
            elif "cyclone" in lowered or "storm" in lowered or "depression" in lowered:
                result["type"] = "cyclone"
            elif "port congestion" in lowered or "berthing" in lowered or "vessel" in lowered or "cci" in lowered:
                result["type"] = "port_congestion"
            elif "accident" in lowered or "closure" in lowered or "blocked" in lowered or "landslide" in lowered:
                result["type"] = "highway_closure"
            elif "fog" in lowered or "rain" in lowered or "weather" in lowered:
                result["type"] = "weather_hazard"
            else:
                result["type"] = "general_disruption"

        # Override with explicit source scaler values
        for src_key, dst_key in [("event_type", "type"), ("severity", "severity")]:
            if raw_signal.get(src_key) is not None:
                result[dst_key] = raw_signal[src_key]
        if raw_signal.get("location"):
            result["location"] = raw_signal["location"]

        if raw_signal.get("eta_hours") is not None:
            result["eta_hours"] = raw_signal["eta_hours"]
        else:
            result["eta_hours"] = self._extract_eta_hours(text)

        return result

    def _extract_eta_hours(self, text: str) -> float:
        lowered = (text or "").lower()
        if any(token in lowered for token in ("active", "ongoing", "now", "currently")):
            return 0.0

        eta_match = re.search(r"(\d+(?:\.\d+)?)\s*(hr|hrs|hour|hours)", lowered)
        if eta_match:
            try:
                return max(0.0, float(eta_match.group(1)))
            except Exception:
                return 0.0
        return 0.0

    def _enrich(self, result: dict, raw_signal: dict) -> dict:
        """Override lat/lon with explicit source coordinates, add metadata."""
        # Source-provided coords always win (e.g. Open-Meteo supplies exact hub coords)
        if raw_signal.get("lat") is not None:
            result["lat"] = float(raw_signal["lat"])
        if raw_signal.get("lon") is not None:
            result["lon"] = float(raw_signal["lon"])

        result.setdefault("lat", 20.5937)
        result.setdefault("lon", 78.9629)
        result.setdefault("radius_km", 25.0)
        result.setdefault("severity", 5)
        result.setdefault("type", "general_disruption")
        result.setdefault("location", "Unknown")
        result.setdefault("eta_hours", self._extract_eta_hours(raw_signal.get("raw_text", "")))

        # Keep values bounded and stable for downstream layers.
        try:
            result["severity"] = max(1, min(10, int(round(float(result.get("severity", 5))))))
        except Exception:
            result["severity"] = 5
        try:
            result["radius_km"] = max(1.0, float(result.get("radius_km", 25.0)))
        except Exception:
            result["radius_km"] = 25.0
        try:
            result["eta_hours"] = max(0.0, float(result.get("eta_hours", 0.0)))
        except Exception:
            result["eta_hours"] = 0.0

        result["text_summary"] = raw_signal.get("raw_text", "")
        result["source"]       = raw_signal.get("source", "unknown")
        return result


# Module-level singleton
rag_processor = LlamaIndexRAGProcessor()
