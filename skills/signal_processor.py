from __future__ import annotations

import json
import os
import re
from typing import Any

from pydantic import ValidationError

from schema import Disruption

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


def parse_disruption_text(text: str) -> Disruption:
    """
    Parse unstructured disruption text into a strict Disruption model.
    Uses Groq when available, otherwise falls back to deterministic heuristics.
    """
    groq_api_key = os.getenv("GROQ_API_KEY")
    if groq_api_key:
        parsed = _parse_with_llm(text, groq_api_key)
        if parsed is not None:
            return parsed
    return _heuristic_parse(text)


def _parse_with_llm(text: str, groq_api_key: str) -> Disruption | None:
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_groq import ChatGroq
    except ImportError:
        return None

    system_prompt = (
        "You extract disruption events for logistics operations. "
        "Return only JSON with keys: disruption_id, event_type, location, "
        "severity, eta_hours, impacted_mode, summary."
    )
    llm = ChatGroq(model=DEFAULT_MODEL, api_key=groq_api_key, temperature=0)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=text),
    ]
    try:
        response = llm.invoke(messages)
        payload = _extract_json_object(response.content)
        if not payload:
            return None
        return Disruption.model_validate(payload)
    except (ValidationError, ValueError, TypeError):
        return None
    except Exception:
        return None


def _extract_json_object(content: Any) -> dict[str, Any] | None:
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        return None

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return None


def _heuristic_parse(text: str) -> Disruption:
    lowered = text.lower()

    event_type = "general_disruption"
    if "flood" in lowered:
        event_type = "flood"
    elif "cyclone" in lowered or "storm" in lowered:
        event_type = "cyclone"
    elif "port congestion" in lowered or "congestion" in lowered:
        event_type = "port_congestion"

    impacted_mode = "road"
    if "port" in lowered or "vessel" in lowered or "marine" in lowered:
        impacted_mode = "sea"

    severity = 5
    if "critical" in lowered or "severe" in lowered:
        severity = 9
    elif "major" in lowered or "high" in lowered:
        severity = 7
    elif "minor" in lowered or "low" in lowered:
        severity = 3

    eta_match = re.search(r"(\d+)\s*(hr|hrs|hour|hours)", lowered)
    eta_hours = int(eta_match.group(1)) if eta_match else 0
    if "active" in lowered or "ongoing" in lowered or "now" in lowered:
        eta_hours = 0

    location = "Unknown"
    location_match = re.search(r"(?:near|at|in)\s+([A-Za-z0-9\-\s]+)", text)
    if location_match:
        location = location_match.group(1).strip(" .,:;")

    disruption_id = re.sub(r"[^a-z0-9]+", "-", f"{event_type}-{location}".lower()).strip("-")
    disruption_id = disruption_id or "disruption-001"

    return Disruption(
        disruption_id=disruption_id,
        event_type=event_type,
        location=location,
        severity=severity,
        eta_hours=eta_hours,
        impacted_mode=impacted_mode,
        summary=text.strip(),
    )
