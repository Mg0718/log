from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


RiskLevel = Literal["Low", "Medium", "High"]


class Shipment(BaseModel):
    shipment_id: str = "UNKNOWN-SHIPMENT"
    origin: str = "Unknown Origin"
    destination: str = "Unknown Destination"
    current_location: str = "Unknown Location"
    route_region: str = "Unknown Region"
    mode: str = "road"
    priority: float = 1.0
    remaining_distance_km: float = 0.0
    route_overlap: float = 1.0
    fuel_rate: float = 1.0
    penalty_rate: float = 100.0
    original_eta_hours: float = 24.0
    base_fuel_distance_km: float = 0.0

    @field_validator("priority", "remaining_distance_km", "route_overlap", "fuel_rate", "penalty_rate", "original_eta_hours", "base_fuel_distance_km")
    @classmethod
    def non_negative(cls, value: float) -> float:
        try:
            return round(max(0.0, float(value)), 2)
        except Exception:
            return 0.0


class RawInputs(BaseModel):
    signal_text: str = ""
    shipment: Shipment = Field(default_factory=Shipment)


class ForecastedDisruption(BaseModel):
    event_type: str = "general_disruption"
    location: str = "Unknown"
    probability: float = 50.0
    severity: float = 5.0
    eta_hours: float = 0.0
    impacted_mode: str = "road"
    summary: str = "No disruption summary available."

    @field_validator("probability")
    @classmethod
    def probability_bounds(cls, value: float) -> float:
        try:
            return round(min(100.0, max(0.0, float(value))), 2)
        except Exception:
            return 50.0

    @field_validator("severity")
    @classmethod
    def severity_bounds(cls, value: float) -> float:
        try:
            return round(min(10.0, max(1.0, float(value))), 2)
        except Exception:
            return 5.0

    @field_validator("eta_hours")
    @classmethod
    def eta_non_negative(cls, value: float) -> float:
        try:
            return round(max(0.0, float(value)), 2)
        except Exception:
            return 0.0


class RiskAssessment(BaseModel):
    risk_score: float = 0.0
    risk_level: RiskLevel = "Low"
    route_overlap: float = 1.0
    explanation: str = "Risk analysis not available."

    @field_validator("risk_score", "route_overlap")
    @classmethod
    def validate_floats(cls, value: float) -> float:
        try:
            return round(max(0.0, float(value)), 2)
        except Exception:
            return 0.0


class DelayPrediction(BaseModel):
    predicted_delay_hours: float = 0.0
    confidence_score: float = 50.0
    explanation: str = "Delay prediction not available."

    @field_validator("predicted_delay_hours")
    @classmethod
    def delay_non_negative(cls, value: float) -> float:
        try:
            return round(max(0.0, float(value)), 2)
        except Exception:
            return 0.0

    @field_validator("confidence_score")
    @classmethod
    def confidence_bounds(cls, value: float) -> float:
        try:
            return round(min(100.0, max(0.0, float(value))), 2)
        except Exception:
            return 50.0


class RouteCandidate(BaseModel):
    route_id: str = "default-route"
    route_name: str = "Default Route"
    eta_hours: float = 24.0
    risk_score: float = 1.0
    fuel_cost: float = 0.0
    optimization_score: float = 0.0
    notes: str = "Default route candidate."

    @field_validator("eta_hours", "risk_score", "fuel_cost", "optimization_score")
    @classmethod
    def route_metric_bounds(cls, value: float) -> float:
        try:
            return round(max(0.0, float(value)), 2)
        except Exception:
            return 0.0


class RouteOptimizationResult(BaseModel):
    alternate_routes: list[RouteCandidate] = Field(default_factory=list)
    selected_route: RouteCandidate = Field(default_factory=RouteCandidate)
    explanation: str = "Route optimization not available."


class CostImpact(BaseModel):
    fuel_cost: float = 0.0
    delay_cost: float = 0.0
    original_cost: float = 0.0
    disruption_cost: float = 0.0
    total_estimated_cost: float = 0.0
    explanation: str = "Cost impact not available."

    @field_validator("fuel_cost", "delay_cost", "original_cost", "disruption_cost", "total_estimated_cost")
    @classmethod
    def cost_bounds(cls, value: float) -> float:
        try:
            return round(max(0.0, float(value)), 2)
        except Exception:
            return 0.0


class FinalRecommendation(BaseModel):
    shipment_id: str = "UNKNOWN-SHIPMENT"
    risk_level: RiskLevel = "Low"
    predicted_delay: float = 0.0
    cost_impact: CostImpact = Field(default_factory=CostImpact)
    recommended_actions: list[str] = Field(default_factory=lambda: ["Continue monitoring"])
    reasoning_log: str = "The system used safe defaults because no detailed reasoning was available."


class AgentState(BaseModel):
    raw_inputs: RawInputs = Field(default_factory=RawInputs)
    forecasted_disruption: ForecastedDisruption = Field(default_factory=ForecastedDisruption)
    risk_assessment: RiskAssessment = Field(default_factory=RiskAssessment)
    delay_prediction: DelayPrediction = Field(default_factory=DelayPrediction)
    route_optimization: RouteOptimizationResult = Field(default_factory=RouteOptimizationResult)
    cost_impact: CostImpact = Field(default_factory=CostImpact)
    recommended_actions: list[str] = Field(default_factory=lambda: ["Continue monitoring"])
    reasoning_steps: list[str] = Field(default_factory=list)
    final_output: FinalRecommendation = Field(default_factory=FinalRecommendation)
