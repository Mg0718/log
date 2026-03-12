from __future__ import annotations

import os
import re
from typing import Any

from pydantic import BaseModel, Field, ValidationError

try:
    from geopy.geocoders import Nominatim
except Exception:
    Nominatim = None

DEFAULT_GROQ_MODEL = "llama3-70b-8192"
FALLBACK_COORDINATES = {
    "Chennai": (13.0827, 80.2707),
    "Jawaharlal Nehru Port": (18.9498, 72.9508),
    "Kolkata": (22.5726, 88.3639),
    "Unknown": (20.5937, 78.9629),
}


class DisruptionEvent(BaseModel):
    event_type: str = "general_disruption"
    location: str = "Unknown"
    severity: int = Field(default=5, ge=1, le=10)
    radius_km: float = Field(default=25.0, ge=1.0)


class SignalProcessor:
    def __init__(self) -> None:
        self.groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.geolocator = Nominatim(user_agent="project_aegis_backend") if Nominatim is not None else None

    def process_signal(self, raw_signal: dict[str, Any]) -> dict[str, Any]:
        text = str(raw_signal.get("raw_text", "")).strip()
        event = self._extract_disruption_event(text)
        lat, lon = self.geocode_location(event.location)
        return {
            "type": event.event_type,
            "lat": lat,
            "lon": lon,
            "radius_km": event.radius_km,
            "severity": event.severity,
            "text_summary": text or "No summary available.",
        }

    def _extract_disruption_event(self, text: str) -> DisruptionEvent:
        if self.groq_api_key:
            event = self._extract_with_llm(text)
            if event is not None:
                return event
        return self._fallback_extract(text)

    def _extract_with_llm(self, text: str) -> DisruptionEvent | None:
        try:
            from langchain_groq import ChatGroq
        except Exception:
            return None

        try:
            llm = ChatGroq(
                model=DEFAULT_GROQ_MODEL,
                api_key=self.groq_api_key,
                temperature=0,
            )
            structured_llm = llm.with_structured_output(DisruptionEvent)
            result = structured_llm.invoke(
                (
                    "Extract a logistics disruption event. "
                    "Return only structured fields for event_type, location, severity, and radius_km."
                )
                + "\n\n"
                + text
            )
            return DisruptionEvent.model_validate(result)
        except (ValidationError, TypeError, ValueError):
            return None
        except Exception:
            return None

    def _fallback_extract(self, text: str) -> DisruptionEvent:
        try:
            lowered = text.lower()

            event_type = "general_disruption"
            if "flood" in lowered or "rainfall" in lowered:
                event_type = "flooding"
            elif "port congestion" in lowered or "berthing" in lowered:
                event_type = "port_congestion"
            elif "cyclone" in lowered:
                event_type = "cyclone"

            severity = 5
            if "severe" in lowered or "halted" in lowered or "worsening" in lowered:
                severity = 8
            elif "warning" in lowered or "likely" in lowered:
                severity = 6

            radius_km = 25.0
            if event_type == "flooding":
                radius_km = 35.0
            elif event_type == "port_congestion":
                radius_km = 18.0
            elif event_type == "cyclone":
                radius_km = 60.0

            location = "Unknown"
            if "jawaharlal nehru port" in lowered:
                location = "Jawaharlal Nehru Port"
            elif "chennai" in lowered:
                location = "Chennai"
            elif "kolkata" in lowered:
                location = "Kolkata"
            else:
                location_match = re.search(
                    r"(?:near|at|for|on)\s+([A-Za-z0-9\-\s]+?)(?:,|\.|\s+with|\s+traffic|\s+vessel|\s+likely|$)",
                    text,
                    re.IGNORECASE,
                )
                if location_match:
                    location = location_match.group(1).strip()

            return DisruptionEvent(
                event_type=event_type,
                location=location,
                severity=severity,
                radius_km=radius_km,
            )
        except Exception:
            return DisruptionEvent()

    def geocode_location(self, location_string: str) -> tuple[float, float]:
        location_key = (location_string or "Unknown").strip()
        try:
            if self.geolocator is not None:
                geocoded = self.geolocator.geocode(location_key, timeout=10)
                if geocoded is not None:
                    return round(float(geocoded.latitude), 6), round(float(geocoded.longitude), 6)
        except Exception:
            pass

        fallback = FALLBACK_COORDINATES.get(location_key)
        if fallback is not None:
            return fallback

        return FALLBACK_COORDINATES["Unknown"]
