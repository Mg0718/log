from __future__ import annotations

from schema import Disruption, RouteOption, Shipment


def find_alternate_route(shipment: Shipment, disruption: Disruption, proactive: bool) -> RouteOption:
    """
    Mock route engine for deterministic hackathon demos.
    """
    if disruption.impacted_mode != shipment.mode and disruption.event_type != "general_disruption":
        return RouteOption(
            route_id=f"{shipment.shipment_id}-monitor",
            status="monitor_only",
            extra_km=0,
            extra_time_hours=0,
            confidence=0.91,
            rationale="Disruption mode does not directly block the shipment mode.",
        )

    base_extra_km = 18 + (disruption.severity * 6)
    base_extra_time = round(base_extra_km / 42, 2)

    if disruption.event_type == "port_congestion":
        base_extra_km = 0
        base_extra_time = 8 + (disruption.severity * 0.7)

    if proactive:
        base_extra_km *= 0.8
        base_extra_time *= 0.85

    no_reroute = disruption.event_type == "port_congestion" and shipment.mode == "sea" and disruption.severity >= 8
    if no_reroute:
        return RouteOption(
            route_id=f"{shipment.shipment_id}-hold",
            status="no_viable_reroute",
            extra_km=0,
            extra_time_hours=base_extra_time,
            confidence=0.62,
            rationale="Congestion is network-wide; no viable berth change is available in the mock engine.",
        )

    return RouteOption(
        route_id=f"{shipment.shipment_id}-alt",
        status="reroute_available",
        extra_km=round(base_extra_km, 2),
        extra_time_hours=round(base_extra_time, 2),
        confidence=0.84 if proactive else 0.79,
        rationale="Alternate route bypasses the disruption corridor with manageable detour impact.",
    )
