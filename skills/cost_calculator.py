from __future__ import annotations

from schema import CostSummary, Disruption, RouteOption, Shipment


def calculate_business_impact(
    shipment: Shipment,
    disruption: Disruption,
    route_option: RouteOption,
) -> tuple[CostSummary, float]:
    detour_cost = round(route_option.extra_km * shipment.fuel_cost_per_km, 2)
    delay_penalty = round(shipment.sla_penalty, 2)
    net_benefit = round(delay_penalty - detour_cost, 2)
    financially_viable = net_benefit >= 0

    score = (
        disruption.severity * 6
        + shipment.priority * 8
        + min(route_option.extra_time_hours * 3, 20)
        + (15 if financially_viable else 0)
    )
    business_impact_score = max(0.0, min(100.0, round(score, 2)))

    return (
        CostSummary(
            detour_cost=detour_cost,
            delay_penalty=delay_penalty,
            net_benefit=net_benefit,
            financially_viable=financially_viable,
        ),
        business_impact_score,
    )
