# Project Aegis Layer 4: Agentic Reasoning

## Purpose

Layer 4 is an autonomous state machine built with LangGraph. It converts disruption signals into validated logistics decisions. The workflow is not a chatbot. It evaluates shipment exposure, predicts or reacts to disruption timing, compares business costs, and emits a strict JSON decision for downstream consumers.

## Four-Agent Architecture

### 1. RiskAnalyst
- Input: `disruption`, `shipment`
- Responsibility:
  - Determine whether the disruption affects the shipment corridor.
  - Score urgency and vulnerability.
  - Create an initial reasoning log entry.
- Key outputs:
  - `risk_level`
  - `affected`
  - `recommended_mode` seed

### 2. RouteOptimizer
- Input: current `AgentState`
- Responsibility:
  - Trigger `Proactive Reroute` when `disruption.eta_hours > 0`.
  - Trigger `Reactive Reroute` when `disruption.eta_hours <= 0`.
  - Request alternate route data from the mocked routing engine.
- Key outputs:
  - `route_option`
  - `action_type`
  - updated reasoning log

### 3. CostAnalyst
- Input: `shipment`, `route_option`, `disruption`
- Responsibility:
  - Apply the Financial Impact Layer.
  - Compute detour cost: `extra_km * fuel_cost_per_km`
  - Compare with SLA penalty.
  - Produce a business impact score and ROI-style recommendation.
- Key outputs:
  - `business_impact_score`
  - `cost_summary`
  - `recommended_mode`

### 4. ActionComposer
- Input: fully populated `AgentState`
- Responsibility:
  - Compose the final frontend-safe JSON.
  - Include a concise but clear `reasoning_log`.
  - Validate against `FinalDecision`.
- Key outputs:
  - `final_decision`

## State Schema

The LangGraph state is defined in `schema.py` as `AgentState`.

### Core fields
- `raw_signal`: unstructured external event text
- `disruption`: normalized disruption object
- `shipment`: shipment context
- `risk_level`: `low | medium | high | critical`
- `affected`: whether the shipment is materially exposed
- `action_type`: `Monitor | Proactive Reroute | Reactive Reroute | Hold`
- `route_option`: proposed route alternative
- `business_impact_score`: normalized 0-100 score
- `cost_summary`: detailed financial comparison
- `recommended_mode`: final machine recommendation
- `reasoning_log`: ordered trace of agent decisions
- `final_decision`: strict JSON payload returned to Member 3

## Reasoning Flow

1. `signal_processor.py` converts raw text into a validated `Disruption`.
2. The graph is initialized with `Disruption` and `Shipment`.
3. `RiskAnalyst` scores vulnerability.
4. `RouteOptimizer` decides predictive vs reactive rerouting.
5. `CostAnalyst` compares detour cost against SLA penalty.
6. `ActionComposer` emits the final `FinalDecision` JSON.

## Predictive Shadow Routing

This layer treats disruption timing as a first-class signal:
- `eta_hours > 0`: the event is incoming, so the engine uses `Proactive Reroute`
- `eta_hours <= 0`: the event is ongoing or already realized, so the engine uses `Reactive Reroute`

This creates a shadow-routing style decision even before operational failure occurs.

## Financial Impact Layer

The business decision is based on:
- `detour_cost = route_option.extra_km * shipment.fuel_cost_per_km`
- `delay_penalty = shipment.sla_penalty`

Decision intent:
- If detour cost is lower than delay penalty, rerouting is financially favorable.
- If detour cost is higher, monitoring or holding may be preferred unless risk is critical.

The `business_impact_score` is a bounded 0-100 value derived from:
- disruption severity
- shipment priority
- route delay added
- cost avoidance from rerouting

## Downstream Contract

The final node returns a `FinalDecision` object with:
- shipment and disruption identifiers
- chosen action
- route details
- cost summary
- business impact score
- reasoning log

Member 3 should consume the serialized `FinalDecision.model_dump()` output as the authoritative UI payload.
