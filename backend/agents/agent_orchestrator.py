from __future__ import annotations

import os
import re
from typing import Any

import requests

from backend.models.schema import (
    AgentState,
    CostImpact,
    DelayPrediction,
    FinalRecommendation,
    ForecastedDisruption,
    RawInputs,
    RiskAssessment,
    RouteCandidate,
    RouteOptimizationResult,
    Shipment,
)
from backend.services.skills.calculators import (
    calculate_cost_impact,
    calculate_optimization_score,
    calculate_risk_score,
    categorize_risk_level,
)

try:
    from langgraph.graph import END, StateGraph
except ImportError:
    END = "__end__"
    StateGraph = None

DEFAULT_GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3-70b-8192")


def _safe_float(value: Any, default: float = 0.0, lower: float = 0.0, upper: float | None = None) -> float:
    try:
        numeric = float(value)
        if upper is not None:
            numeric = min(upper, numeric)
        numeric = max(lower, numeric)
        return round(numeric, 2)
    except Exception:
        return round(default, 2)


def _append_reason(state: AgentState, message: str) -> AgentState:
    try:
        state.reasoning_steps.append(message)
    except Exception:
        state.reasoning_steps = [message]
    return state


def _safe_forecast_from_text(signal_text: str) -> ForecastedDisruption:
    text = signal_text or ""
    lowered = text.lower()

    event_type = "general_disruption"
    if "flood" in lowered:
        event_type = "flood"
    elif "cyclone" in lowered or "storm" in lowered:
        event_type = "cyclone"
    elif "port congestion" in lowered or "congestion" in lowered:
        event_type = "port_congestion"
    elif "strike" in lowered:
        event_type = "labor_strike"

    impacted_mode = "road"
    if any(token in lowered for token in ("port", "vessel", "marine", "berth")):
        impacted_mode = "sea"
    elif any(token in lowered for token in ("rail", "train")):
        impacted_mode = "rail"

    severity = 5.0
    if "critical" in lowered or "severe" in lowered:
        severity = 9.0
    elif "major" in lowered or "high" in lowered:
        severity = 7.0
    elif "minor" in lowered or "low" in lowered:
        severity = 3.0

    probability = 50.0
    probability_match = re.search(r"(\d{1,3})\s*%", lowered)
    if probability_match:
        probability = _safe_float(probability_match.group(1), default=50.0, lower=0.0, upper=100.0)
    elif any(token in lowered for token in ("expected", "forecast", "likely", "warning")):
        probability = 85.0
    elif any(token in lowered for token in ("possible", "watch")):
        probability = 65.0

    eta_hours = 0.0
    eta_match = re.search(r"(\d+(?:\.\d+)?)\s*(hr|hrs|hour|hours)", lowered)
    if eta_match:
        eta_hours = _safe_float(eta_match.group(1), default=0.0, lower=0.0)
    if any(token in lowered for token in ("active", "ongoing", "now", "currently")):
        eta_hours = 0.0

    location = "Unknown"
    location_match = re.search(
        r"(?:near|at|in)\s+([A-Za-z0-9\-\s]+?)(?:\s+with|\s+expected|\s+forecast|\s+\d+\s*(?:hr|hrs|hour|hours|%)|[.,]|$)",
        text,
        re.IGNORECASE,
    )
    if location_match:
        location = location_match.group(1).strip(" .,:;")

    return ForecastedDisruption(
        event_type=event_type,
        location=location,
        probability=probability,
        severity=severity,
        eta_hours=eta_hours,
        impacted_mode=impacted_mode,
        summary=text.strip() or "No signal text provided.",
    )


def _get_llm():
    """
    Return the best available LLM client.
    Priority:
      1. Google Gemini (free tier) — set GEMINI_API_KEY from aistudio.google.com
      2. Groq (free tier) — set GROQ_API_KEY from console.groq.com
      3. None — pipeline continues with deterministic fallback (no LLM required)
    """
    # 1. Google Gemini free tier
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    if gemini_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            return ChatGoogleGenerativeAI(
                model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
                google_api_key=gemini_key,
                temperature=0,
            )
        except Exception:
            pass

    # 2. Groq free tier fallback
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    if groq_key:
        try:
            from langchain_groq import ChatGroq

            return ChatGroq(model=DEFAULT_GROQ_MODEL, api_key=groq_key, temperature=0)
        except Exception:
            pass

    # 3. No key configured — deterministic fallback handles everything
    return None


def pre_disruption_detection_agent(state: AgentState) -> AgentState:
    raw_text = state.raw_inputs.signal_text
    fallback = ForecastedDisruption()

    llm = _get_llm()
    if llm is not None:
        try:
            structured_llm = llm.with_structured_output(ForecastedDisruption)
            parsed = structured_llm.invoke(
                (
                    "Forecast logistics disruptions from the input. "
                    "Return only fields required by the schema. "
                    "If uncertain, keep safe defaults."
                )
                + "\n\n"
                + raw_text
            )
            state.forecasted_disruption = ForecastedDisruption.model_validate(parsed)
            return _append_reason(
                state,
                "Pre-Disruption Detection Agent parsed the incoming signal with structured LLM output.",
            )
        except Exception:
            pass

    try:
        state.forecasted_disruption = _safe_forecast_from_text(raw_text)
        return _append_reason(
            state,
            "Pre-Disruption Detection Agent used deterministic fallback parsing with default-safe values.",
        )
    except Exception:
        state.forecasted_disruption = fallback
        return _append_reason(
            state,
            "Pre-Disruption Detection Agent fell back to severity 5 and probability 50 because parsing failed.",
        )


def risk_analysis_agent(state: AgentState) -> AgentState:
    try:
        shipment = state.raw_inputs.shipment
        disruption = state.forecasted_disruption
        route_overlap = _safe_float(shipment.route_overlap, default=1.0, lower=0.0)
        risk_score = calculate_risk_score(disruption.severity, route_overlap, shipment.priority)
        risk_level = categorize_risk_level(risk_score)
        state.risk_assessment = RiskAssessment(
            risk_score=risk_score,
            risk_level=risk_level,
            route_overlap=route_overlap,
            explanation=(
                "Risk Score = Disruption Severity * Route Overlap * Shipment Priority. "
                f"Computed as {disruption.severity} * {route_overlap} * {shipment.priority}."
            ),
        )
        return _append_reason(
            state,
            f"Risk Analysis Agent computed risk_score={risk_score} and categorized it as {risk_level}.",
        )
    except Exception:
        state.risk_assessment = RiskAssessment(
            risk_score=0.0,
            risk_level="Low",
            route_overlap=1.0,
            explanation="Risk analysis failed, so the system defaulted to a low-risk safe object.",
        )
        return _append_reason(state, "Risk Analysis Agent failed safely and returned default low-risk output.")


def delay_prediction_agent(state: AgentState) -> AgentState:
    try:
        disruption = state.forecasted_disruption
        shipment = state.raw_inputs.shipment
        predicted_delay_hours = _safe_float(
            (disruption.severity * max(shipment.remaining_distance_km, 1.0)) / 250.0,
            default=0.0,
            lower=0.0,
        )
        confidence_score = _safe_float(
            55.0 + (disruption.probability * 0.25) + (state.risk_assessment.route_overlap * 5.0),
            default=50.0,
            lower=0.0,
            upper=100.0,
        )
        state.delay_prediction = DelayPrediction(
            predicted_delay_hours=predicted_delay_hours,
            confidence_score=confidence_score,
            explanation=(
                "Delay Prediction Agent estimated delay from disruption severity and remaining distance "
                f"({disruption.severity} and {shipment.remaining_distance_km} km)."
            ),
        )
        return _append_reason(
            state,
            f"Delay Prediction Agent estimated {predicted_delay_hours} hours of delay with {confidence_score}% confidence.",
        )
    except Exception:
        state.delay_prediction = DelayPrediction(
            predicted_delay_hours=0.0,
            confidence_score=50.0,
            explanation="Delay prediction failed, so safe defaults were used.",
        )
        return _append_reason(state, "Delay Prediction Agent failed safely and returned default delay output.")


def route_optimization_agent(state: AgentState) -> AgentState:
    try:
        shipment = state.raw_inputs.shipment
        disruption = state.forecasted_disruption
        delay = state.delay_prediction.predicted_delay_hours
        base_distance = shipment.base_fuel_distance_km or shipment.remaining_distance_km or 100.0
        base_eta = shipment.original_eta_hours or max(shipment.remaining_distance_km / 45.0, 1.0)
        route_overlap = state.risk_assessment.route_overlap or 1.0

        external_route = _query_route_provider(shipment)
        provider_note = "heuristic"
        if external_route is not None:
            base_distance = _safe_float(external_route["distance_km"], default=base_distance, lower=1.0)
            base_eta = _safe_float(external_route["eta_hours"], default=base_eta, lower=0.1)
            provider_note = external_route.get("provider", "external")

        candidate_specs = [
            {
                "route_id": "route-a",
                "route_name": "Bypass Corridor A",
                "eta_hours": _safe_float(base_eta + (delay * 0.65), default=base_eta, lower=0.0),
                "risk_score": _safe_float(state.risk_assessment.risk_score * 0.7, default=state.risk_assessment.risk_score, lower=0.0),
                "fuel_cost": _safe_float((base_distance * 1.08) * shipment.fuel_rate, default=0.0, lower=0.0),
                "notes": f"Moderate detour with lower corridor exposure ({provider_note} baseline).",
            },
            {
                "route_id": "route-b",
                "route_name": "Bypass Corridor B",
                "eta_hours": _safe_float(base_eta + (delay * 0.45), default=base_eta, lower=0.0),
                "risk_score": _safe_float(max(0.1, state.risk_assessment.risk_score * (0.5 if disruption.eta_hours > 0 else 0.8)), default=state.risk_assessment.risk_score, lower=0.0),
                "fuel_cost": _safe_float((base_distance * 1.18) * shipment.fuel_rate, default=0.0, lower=0.0),
                "notes": f"Faster detour with higher fuel burn but lower exposure ({provider_note} baseline).",
            },
        ]

        alternate_routes: list[RouteCandidate] = []
        for spec in candidate_specs:
            try:
                optimization_score = calculate_optimization_score(
                    spec["eta_hours"],
                    spec["risk_score"],
                    spec["fuel_cost"],
                )
                alternate_routes.append(
                    RouteCandidate(
                        route_id=spec["route_id"],
                        route_name=spec["route_name"],
                        eta_hours=spec["eta_hours"],
                        risk_score=spec["risk_score"],
                        fuel_cost=spec["fuel_cost"],
                        optimization_score=optimization_score,
                        notes=spec["notes"],
                    )
                )
            except Exception:
                alternate_routes.append(RouteCandidate())

        selected_route = min(alternate_routes, key=lambda route: route.optimization_score)
        state.route_optimization = RouteOptimizationResult(
            alternate_routes=alternate_routes,
            selected_route=selected_route,
            explanation=(
                "Route Optimization Agent evaluated at least two alternate routes using "
                "Optimization Score = (ETA * 0.4) + (Risk * 0.3) + (Fuel Cost * 0.3). "
                f"Route baseline source: {provider_note}."
            ),
        )
        return _append_reason(
            state,
            f"Route Optimization Agent selected {selected_route.route_name} with score {selected_route.optimization_score} (provider={provider_note}).",
        )
    except Exception:
        default_route = RouteCandidate()
        state.route_optimization = RouteOptimizationResult(
            alternate_routes=[default_route, default_route],
            selected_route=default_route,
            explanation="Route optimization failed, so a default route object was returned.",
        )
        return _append_reason(state, "Route Optimization Agent failed safely and returned default route options.")


def _query_route_provider(shipment: Shipment) -> dict[str, float | str] | None:
    """
    Try live route engines (MapmyIndia/OpenRouteService) for ETA + distance baseline.
    Falls back to None when providers are unavailable.
    """
    current_lat = _safe_float(getattr(shipment, "current_lat", 0.0), default=0.0, lower=-90.0, upper=90.0)
    current_lon = _safe_float(getattr(shipment, "current_lon", 0.0), default=0.0, lower=-180.0, upper=180.0)

    # Destination lookup from known city list if available.
    destination_lat, destination_lon = 0.0, 0.0
    try:
        from backend.services.layer3_knowledge import get_city_coords_or_none

        maybe_dest = get_city_coords_or_none(getattr(shipment, "destination", ""))
        if maybe_dest:
            destination_lat, destination_lon = maybe_dest
    except Exception:
        pass

    if destination_lat == 0.0 and destination_lon == 0.0:
        return None

    # MapmyIndia attempt (when API key configured). Endpoint availability may vary by plan.
    mappls_key = os.getenv("MAPPLS_REST_API_KEY", "").strip()
    if mappls_key:
        try:
            url = (
                "https://apis.mappls.com/advancedmaps/v1/"
                f"{mappls_key}/route_adv/driving/"
                f"{current_lon},{current_lat};{destination_lon},{destination_lat}"
            )
            resp = requests.get(url, timeout=6)
            if resp.status_code == 200:
                payload = resp.json()
                routes = payload.get("routes") or payload.get("route") or []
                if routes:
                    route = routes[0]
                    dist_km = _safe_float(route.get("distance", 0.0) / 1000.0, default=0.0, lower=0.0)
                    eta_h = _safe_float(route.get("duration", 0.0) / 3600.0, default=0.0, lower=0.0)
                    if dist_km > 0 and eta_h >= 0:
                        return {"provider": "mapmyindia", "distance_km": dist_km, "eta_hours": eta_h}
        except Exception:
            pass

    # OpenRouteService attempt (when API key configured).
    ors_key = os.getenv("OPENROUTESERVICE_API_KEY", "").strip()
    if ors_key:
        try:
            url = "https://api.openrouteservice.org/v2/directions/driving-car/json"
            body = {
                "coordinates": [
                    [current_lon, current_lat],
                    [destination_lon, destination_lat],
                ]
            }
            resp = requests.post(
                url,
                headers={
                    "Authorization": ors_key,
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=6,
            )
            if resp.status_code == 200:
                payload = resp.json()
                routes = payload.get("routes", [])
                if routes:
                    summary = routes[0].get("summary", {})
                    dist_km = _safe_float(summary.get("distance", 0.0) / 1000.0, default=0.0, lower=0.0)
                    eta_h = _safe_float(summary.get("duration", 0.0) / 3600.0, default=0.0, lower=0.0)
                    if dist_km > 0 and eta_h >= 0:
                        return {"provider": "openrouteservice", "distance_km": dist_km, "eta_hours": eta_h}
        except Exception:
            pass

    return None


def risk_analyst_agent(state: AgentState) -> AgentState:
    """Layer 4 Agent 1: RiskAnalyst."""
    state = pre_disruption_detection_agent(state)
    state = risk_analysis_agent(state)
    state = delay_prediction_agent(state)
    return _append_reason(state, "RiskAnalyst completed forecast + risk + delay analysis.")


def route_optimizer_agent(state: AgentState) -> AgentState:
    """Layer 4 Agent 2: RouteOptimizer."""
    state = route_optimization_agent(state)
    return _append_reason(state, "RouteOptimizer completed alternate route scoring and selection.")


def action_composer_agent(state: AgentState) -> AgentState:
    """Layer 4 Agent 3: ActionComposer."""
    state = cost_impact_agent(state)
    state = action_recommendation_agent(state)
    return _append_reason(state, "ActionComposer produced final recommendation payload.")


def cost_impact_agent(state: AgentState) -> AgentState:
    try:
        shipment = state.raw_inputs.shipment
        selected_route = state.route_optimization.selected_route
        predicted_delay = state.delay_prediction.predicted_delay_hours
        base_distance = shipment.base_fuel_distance_km or shipment.remaining_distance_km

        state.cost_impact = calculate_cost_impact(
            distance_km=selected_route.fuel_cost / max(shipment.fuel_rate, 0.01),
            fuel_rate=shipment.fuel_rate,
            delay_hours=predicted_delay,
            penalty_rate=shipment.penalty_rate,
            original_distance_km=base_distance,
        )
        state.cost_impact.explanation = (
            "Cost Impact Agent used the required formulas: Fuel Cost = Distance * Fuel Rate, "
            "Delay Cost = Delay Hours * Penalty Rate, Total Cost = Fuel Cost + Delay Cost."
        )
        return _append_reason(
            state,
            f"Cost Impact Agent estimated total_estimated_cost={state.cost_impact.total_estimated_cost}.",
        )
    except Exception:
        state.cost_impact = CostImpact(
            fuel_cost=0.0,
            delay_cost=0.0,
            original_cost=0.0,
            disruption_cost=0.0,
            total_estimated_cost=0.0,
            explanation="Cost calculation failed, so safe default cost values were returned.",
        )
        return _append_reason(state, "Cost Impact Agent failed safely and returned default costs.")


def action_recommendation_agent(state: AgentState) -> AgentState:
    try:
        actions: list[str] = []
        if state.risk_assessment.risk_level == "High":
            actions.append("Escalate shipment to control tower")
        if state.forecasted_disruption.eta_hours > 0:
            actions.append("Initiate proactive reroute before disruption onset")
        else:
            actions.append("Reroute or hold based on current network blockage")
        if state.cost_impact.disruption_cost > state.cost_impact.original_cost:
            actions.append("Notify customer of potential SLA impact")
        actions.append(f"Use selected route: {state.route_optimization.selected_route.route_name}")

        reasoning_log = (
            "LangGraph Agent Chain: RiskAnalyst -> RouteOptimizer -> ActionComposer. "
            f"Shipment {state.raw_inputs.shipment.shipment_id} was evaluated through this 3-agent flow. "
            f"The system forecast a {state.forecasted_disruption.event_type} disruption near {state.forecasted_disruption.location} "
            f"with {state.forecasted_disruption.probability}% probability and severity {state.forecasted_disruption.severity}. "
            f"Risk was classified as {state.risk_assessment.risk_level} from the required severity-overlap-priority formula. "
            f"The predicted delay is {state.delay_prediction.predicted_delay_hours} hours at "
            f"{state.delay_prediction.confidence_score}% confidence. "
            f"The selected route is {state.route_optimization.selected_route.route_name}, chosen by the lowest optimization score. "
            f"Estimated total cost under disruption is {state.cost_impact.total_estimated_cost}. "
            f"Recommended actions were generated deterministically to keep the frontend contract stable. "
            f"Reasoning trace: {' | '.join(state.reasoning_steps)}"
        )

        state.recommended_actions = actions
        state.final_output = FinalRecommendation(
            shipment_id=state.raw_inputs.shipment.shipment_id,
            risk_level=state.risk_assessment.risk_level,
            predicted_delay=state.delay_prediction.predicted_delay_hours,
            cost_impact=state.cost_impact,
            recommended_actions=actions,
            reasoning_log=reasoning_log,
        )
        return _append_reason(state, "Action Recommendation Agent compiled the final frontend-safe JSON payload.")
    except Exception:
        state.final_output = FinalRecommendation(
            shipment_id=state.raw_inputs.shipment.shipment_id,
            risk_level="Low",
            predicted_delay=0.0,
            cost_impact=CostImpact(),
            recommended_actions=["Continue monitoring"],
            reasoning_log="The final recommendation agent encountered an issue and returned a safe default payload.",
        )
        return _append_reason(state, "Action Recommendation Agent failed safely and returned default final output.")


def build_graph():
    if StateGraph is None:
        return _FallbackGraph()

    graph = StateGraph(AgentState)
    graph.add_node("RiskAnalyst", risk_analyst_agent)
    graph.add_node("RouteOptimizer", route_optimizer_agent)
    graph.add_node("ActionComposer", action_composer_agent)
    graph.set_entry_point("RiskAnalyst")
    graph.add_edge("RiskAnalyst", "RouteOptimizer")
    graph.add_edge("RouteOptimizer", "ActionComposer")
    graph.add_edge("ActionComposer", END)
    return graph.compile()


class _FallbackGraph:
    def invoke(self, initial_state: AgentState) -> AgentState:
        state = initial_state
        for node in (
            risk_analyst_agent,
            route_optimizer_agent,
            action_composer_agent,
        ):
            try:
                state = node(state)
            except Exception:
                state = _append_reason(state, f"Fallback executor caught an unexpected error in {node.__name__}.")
        return state


def _coerce_state_input(mock_data: dict[str, Any]) -> AgentState:
    try:
        shipment_payload = mock_data.get("shipment", {})
        raw_inputs = RawInputs(
            signal_text=str(mock_data.get("signal_text", "")),
            shipment=Shipment.model_validate(shipment_payload),
        )
        return AgentState(raw_inputs=raw_inputs)
    except Exception:
        return AgentState()


def run_pipeline(mock_data: dict[str, Any]) -> dict[str, Any]:
    app = build_graph()
    initial_state = _coerce_state_input(mock_data)
    try:
        result = app.invoke(initial_state)
        state = result if isinstance(result, AgentState) else AgentState.model_validate(result)
        if not isinstance(state.final_output, FinalRecommendation):
            state.final_output = FinalRecommendation()
        return state.final_output.model_dump()
    except Exception:
        fallback = FinalRecommendation()
        return fallback.model_dump()


if __name__ == "__main__":
    demo_payload = {
        "signal_text": "Cyclone warning in East Coast Corridor with 85% probability expected in 6 hours.",
        "shipment": {
            "shipment_id": "SHP-DEMO-006",
            "origin": "Chennai",
            "destination": "Visakhapatnam",
            "current_location": "Nellore",
            "route_region": "East Coast Corridor",
            "mode": "road",
            "priority": 4,
            "remaining_distance_km": 620,
            "route_overlap": 0.9,
            "fuel_rate": 2.8,
            "penalty_rate": 160.0,
            "original_eta_hours": 14.0,
            "base_fuel_distance_km": 620,
        },
    }
    print(run_pipeline(demo_payload))
