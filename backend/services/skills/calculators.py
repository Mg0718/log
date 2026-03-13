from __future__ import annotations

from backend.models.schema import CostImpact


def _safe_number(value: float, default: float = 0.0) -> float:
    try:
        return round(float(value), 2)
    except Exception:
        return round(default, 2)


def calculate_risk_score(disruption_severity: float, route_overlap: float, shipment_priority: float) -> float:
    """
    Risk Score = Disruption Severity * Route Overlap * Shipment Priority
    """
    try:
        severity = max(0.0, _safe_number(disruption_severity, 5.0))
        overlap = max(0.0, _safe_number(route_overlap, 1.0))
        priority = max(0.0, _safe_number(shipment_priority, 1.0))
        return round(severity * overlap * priority, 2)
    except Exception:
        return 0.0


def categorize_risk_level(risk_score: float) -> str:
    try:
        score = max(0.0, _safe_number(risk_score, 0.0))
        if score < 3:
            return "Low"
        if score < 6:
            return "Medium"
        return "High"
    except Exception:
        return "Low"


def calculate_optimization_score(eta_hours: float, risk: float, fuel_cost: float) -> float:
    """
    Optimization Score = (ETA * 0.4) + (Risk * 0.3) + (Fuel Cost * 0.3)
    """
    try:
        eta = max(0.0, _safe_number(eta_hours, 24.0))
        route_risk = max(0.0, _safe_number(risk, 1.0))
        fuel = max(0.0, _safe_number(fuel_cost, 0.0))
        return round((eta * 0.4) + (route_risk * 0.3) + (fuel * 0.3), 2)
    except Exception:
        return 0.0


def calculate_cost_impact(
    distance_km: float,
    fuel_rate: float,
    delay_hours: float,
    penalty_rate: float,
    original_distance_km: float,
) -> CostImpact:
    """
    Fuel Cost = Distance * Fuel Rate
    Delay Cost = Delay Hours * Penalty Rate
    Total Cost = Fuel Cost + Delay Cost
    """
    try:
        safe_distance = max(0.0, _safe_number(distance_km, 0.0))
        safe_fuel_rate = max(0.0, _safe_number(fuel_rate, 1.0))
        safe_delay_hours = max(0.0, _safe_number(delay_hours, 0.0))
        safe_penalty_rate = max(0.0, _safe_number(penalty_rate, 0.0))
        safe_original_distance = max(0.0, _safe_number(original_distance_km, 0.0))

        fuel_cost = round(safe_distance * safe_fuel_rate, 2)
        delay_cost = round(safe_delay_hours * safe_penalty_rate, 2)
        original_cost = round(safe_original_distance * safe_fuel_rate, 2)
        disruption_cost = round(fuel_cost + delay_cost, 2)
        total_estimated_cost = disruption_cost

        return CostImpact(
            fuel_cost=fuel_cost,
            delay_cost=delay_cost,
            original_cost=original_cost,
            disruption_cost=disruption_cost,
            total_estimated_cost=total_estimated_cost,
        )
    except Exception:
        return CostImpact()
