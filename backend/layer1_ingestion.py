from __future__ import annotations


def get_raw_signals() -> list[dict]:
    """
    Return simulated raw disruption signals for downstream processing.
    """
    try:
        return [
            {
                "source": "mock_news",
                "raw_text": "Heavy rainfall causes severe flooding on NH48 near Chennai, traffic halted.",
            },
            {
                "source": "mock_port_ops",
                "raw_text": "Port congestion worsening at Jawaharlal Nehru Port, vessel berthing delayed and container movement slowed.",
            },
            {
                "source": "mock_weather_alert",
                "raw_text": "Cyclone warning issued for Kolkata corridor with likely highway disruption in the next 8 hours.",
            },
        ]
    except Exception:
        return [
            {
                "source": "fallback",
                "raw_text": "Heavy rainfall causes severe flooding on NH48 near Chennai, traffic halted.",
            }
        ]
