import asyncio
import json
import logging
import os
import time
import uuid
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from backend.auth import authenticate_user, create_access_token, decode_token

# Layer 1 — Signal ingestion (real APIs: GDELT, Open-Meteo, MapmyIndia, GoComet)
from backend.services.layer1_ingestion import fetch_all_signals, get_raw_signals
# Layer 2 — LlamaIndex RAG processor (DisruptionObject extraction)
from backend.services.layer2_rag import rag_processor
# Layer 2 (legacy) — rule-based processor kept as fallback
from backend.services.layer2_processing import SignalProcessor
# Layer 3 — NetworkX ontology graph (digital twin + auto-trigger intersection query)
from backend.services.layer3_ontology import ontology_graph
# Layer 3 (knowledge) — OSRM route fetch + at-risk shipment lookup
from backend.services.layer3_knowledge import ShipmentKnowledgeModel, get_city_coords_or_none, list_known_cities
# Layer 4 — Kafka-lite event stream (Redis / asyncio.Queue)
from backend.services.event_stream import event_stream
# Layer 4 — LangGraph AI agents (RiskAnalyst → RouteOptimizer → ActionComposer)
from backend.agents.agent_orchestrator import run_pipeline

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SIGNAL_POLL_INTERVAL_SECONDS = int(os.getenv("SIGNAL_POLL_INTERVAL_SECONDS", "30"))
AUTONOMOUS_CHECK_LEAD_MINUTES = int(os.getenv("AUTONOMOUS_CHECK_LEAD_MINUTES", "30"))

app = FastAPI(title="LogosGotham API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory state
class State:
    def __init__(self):
        self.shipments = []
        self.disruptions = []
        self.active_payload = None
        self.notifications = []
        self.connections: List[WebSocket] = []
        self.knowledge_model = ShipmentKnowledgeModel()
        self.processor = SignalProcessor()
        
        # Initialize shipments from knowledge model
        for s in self.knowledge_model.shipments:
            # _get_city_coords returns (lat, lon)
            origin_coord = self.knowledge_model._get_city_coords(s["origin"])
            dest_coord = self.knowledge_model._get_city_coords(s["destination"])
            route = self.knowledge_model.fetch_osrm_route(origin_coord, dest_coord)  # [(lon, lat), ...]
            shipment = {
                "id": s["shipment_id"],
                "cargo": f"Cargo {s['shipment_id']}",
                "priority": s["priority"].upper(),
                "currentRoute": route,
                # Real GPS pin for the truck (origin city coordinates)
                "currentLat": origin_coord[0],
                "currentLon": origin_coord[1],
                "riskScore": 0,
                "monitoringStartTs": 0,
                "lastMitigatedDisruptionId": None,
                "createdAt": 0,
                "source": "seed_data",
                "shipment_details": s  # Raw data for agent
            }
            self.shipments.append(shipment)
            # Seed the NetworkX ontology graph with this shipment node
            ontology_graph.add_shipment(shipment)

state = State()

# Helper for city coords
def get_city_coords(city_name):
    from backend.services.layer3_knowledge import CITY_COORDS
    return CITY_COORDS.get(city_name, (20.5937, 78.9629))


# ── Auth ─────────────────────────────────────────────────────────────────────
http_bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer),
) -> dict:
    """Validate JWT and return user payload. Raises 401 on failure."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Please login at /auth/login.",
        )
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )
    return payload


@app.post("/auth/login")
def auth_login(req: LoginRequest):
    """Authenticate with username and password. Returns a JWT access token."""
    user = authenticate_user(req.username, req.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )
    token = create_access_token({"sub": user["username"], "role": user["role"]})
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
        "full_name": user["full_name"],
    }


@app.get("/auth/me")
def auth_me(current_user: dict = Depends(get_current_user)):
    """Return the currently authenticated user's info."""
    return {"username": current_user.get("sub"), "role": current_user.get("role")}


# ── Transport Schemas ─────────────────────────────────────────────────────────
class ScheduleTransportRequest(BaseModel):
    origin: str
    destination: str
    cargo: str = "General Cargo"
    priority: str = "MEDIUM"
    start_in_minutes: int = 0


class GPSUpdateRequest(BaseModel):
    lat: float
    lon: float
    source: str = "truck_telematics"


class NotifyStakeholdersRequest(BaseModel):
    seller_contact: str = "seller@logogotham.ai"
    receiver_contact: str = "receiver@logogotham.ai"
    note: str = "Operational update generated by autonomous agent"


class SignalInjectRequest(BaseModel):
    signal_type: str = "auto"  # auto | weather | port_congestion | road_closure | customs_delay | civil_unrest


class AgentDecisionRequest(BaseModel):
    shipment_id: str
    decision: str


def _normalize_priority(priority: str) -> str:
    normalized = (priority or "MEDIUM").upper()
    if normalized not in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}:
        return "MEDIUM"
    return normalized


def _priority_score(priority: str) -> int:
    scores = {"LOW": 1, "MEDIUM": 3, "HIGH": 5, "CRITICAL": 7}
    return scores.get(priority, 3)


def _build_shipment_context(shipment: Dict[str, Any], disruption: Dict[str, Any]) -> Dict[str, Any]:
    details = shipment.get("shipment_details", {})
    geo_risk = _compute_geospatial_risk(shipment, disruption)
    return {
        "shipment_id": shipment.get("id"),
        "origin": details.get("origin", "Unknown"),
        "destination": details.get("destination", "Unknown"),
        "current_location": details.get("origin", "Unknown"),
        "current_lat": shipment.get("currentLat", 20.5937),
        "current_lon": shipment.get("currentLon", 78.9629),
        "route_region": disruption.get("type", "general_disruption"),
        "mode": details.get("mode", "road"),
        "priority": details.get("priority_score", _priority_score(shipment.get("priority", "MEDIUM"))),
        "remaining_distance_km": details.get("remaining_distance_km", 500.0),
        "route_overlap": geo_risk.get("overlap_percent", 0.0) / 100.0,
        "overlap_percent": geo_risk.get("overlap_percent", 0.0),
        "fuel_rate": details.get("fuel_rate", 2.5),
        "penalty_rate": details.get("penalty_rate", 130.0),
        "original_eta_hours": details.get("original_eta_hours", 12.0),
        "base_fuel_distance_km": details.get("base_fuel_distance_km", 500.0),
    }


def _compute_geospatial_risk(shipment: Dict[str, Any], disruption: Dict[str, Any]) -> Dict[str, Any]:
    """Layer 4 Geospatial Matching Engine: severity * overlap% * urgency_weight."""
    try:
        route_coords = [
            (float(c[0]), float(c[1]))
            for c in shipment.get("currentRoute", [])
            if isinstance(c, (list, tuple)) and len(c) >= 2
        ]
        polygon_rings = disruption.get("polygonGeoJSON", [[]])
        exterior_ring = polygon_rings[0] if polygon_rings else []
        severity = float(disruption.get("severity", 5.0))
        details = shipment.get("shipment_details", {})
        priority_s = details.get("priority_score", _priority_score(shipment.get("priority", "MEDIUM")))
        # Map priority_score 1–7 to urgency_weight 1.0–2.0
        urgency_weight = 1.0 + (priority_s - 1) / 6.0
        return state.knowledge_model.calculate_geospatial_risk(
            route_coords=route_coords,
            disruption_polygon=exterior_ring,
            severity=severity,
            urgency_weight=urgency_weight,
        )
    except Exception:
        return {"at_risk": False, "overlap_percent": 0.0, "final_risk_score": 0}


def _shipment_intersects_disruption(shipment: Dict[str, Any], disruption: Dict[str, Any]) -> bool:
    """Returns True if the Shapely polygon intersection says this route is at risk."""
    return _compute_geospatial_risk(shipment, disruption).get("at_risk", False)


def _ensure_disruption(disruption_data: Dict[str, Any]) -> Dict[str, Any]:
    matching_disruption = next(
        (
            disruption
            for disruption in state.disruptions
            if disruption["lat"] == disruption_data["lat"]
            and disruption["lon"] == disruption_data["lon"]
        ),
        None,
    )

    if matching_disruption is not None:
        return matching_disruption

    disruption_id = f"EVT-{uuid.uuid4().hex[:4].upper()}"
    lat, lon = disruption_data["lat"], disruption_data["lon"]
    radius = disruption_data.get("radius_km", 25.0) / 111.0
    polygon = [
        [lon + radius, lat + radius],
        [lon + radius, lat - radius],
        [lon - radius, lat - radius],
        [lon - radius, lat + radius],
        [lon + radius, lat + radius],
    ]

    new_disruption = {
        "id": disruption_id,
        "type": disruption_data["type"].upper().replace(" ", "_"),
        "polygonGeoJSON": [polygon],
        "severity": disruption_data["severity"],
        "lat": lat,
        "lon": lon,
        "radius_km": disruption_data.get("radius_km", 25.0),
        "source": disruption_data.get("source", "unknown"),
    }
    state.disruptions.append(new_disruption)
    at_risk_ids = ontology_graph.add_disruption_zone(new_disruption)
    logger.info(f"Ontology auto-query: {disruption_id} at_risk -> {at_risk_ids}")
    return new_disruption


def _reroute_shipment_for_disruption(shipment: Dict[str, Any], disruption: Dict[str, Any]) -> bool:
    shipment_id = shipment.get("id")
    if not shipment_id:
        return False

    context = _build_shipment_context(shipment, disruption)
    signal_text = disruption.get("source", "") or disruption.get("type", "")
    agent_result = run_pipeline({"signal_text": signal_text, "shipment": context})

    destination = shipment.get("shipment_details", {}).get("destination")
    if not destination:
        return False

    dest_coord = state.knowledge_model._get_city_coords(destination)
    current_lat = float(shipment.get("currentLat", 20.5937))
    current_lon = float(shipment.get("currentLon", 78.9629))
    alt_route = state.knowledge_model.fetch_osrm_route((current_lat, current_lon), dest_coord)
    if not alt_route:
        return False

    # Use Shapely-computed risk score (severity * overlap% * urgency_weight → 0–100)
    geo_risk = _compute_geospatial_risk(shipment, disruption)
    computed_risk = geo_risk.get("final_risk_score", 80)
    shipment["riskScore"] = max(int(shipment.get("riskScore", 0)), computed_risk, 55)
    shipment["currentRoute"] = alt_route
    shipment["lastMitigatedDisruptionId"] = disruption.get("id")

    # Frontend-friendly ActionComposer payload so HUD shows backend agent output.
    recommended_actions = agent_result.get("recommended_actions", [])
    driver_msg = (
        recommended_actions[0]
        if recommended_actions
        else f"Shipment {shipment_id}: reroute immediately due to {disruption.get('type', 'DISRUPTION')}."
    )
    customer_msg = (
        f"Shipment {shipment_id} has been proactively rerouted by the AI control tower. "
        f"Current risk score: {shipment['riskScore']}%. "
        f"Route overlap with hazard: {geo_risk.get('overlap_percent', 0.0)}%."
    )
    decision_options = [
        {
            "id": "reroute-now",
            "label": "Approve Reroute",
            "description": "Use alternate corridor immediately",
            "decision": "APPROVE_REROUTE",
        },
        {
            "id": "safe-wait",
            "label": "Safe Wait 30 Min",
            "description": "Hold the truck at a safe stop and reassess",
            "decision": "SAFE_WAIT",
        },
        {
            "id": "escalate",
            "label": "Escalate to Dispatch",
            "description": "Request human intervention and seller approval",
            "decision": "ESCALATE",
        },
    ]
    state.active_payload = {
        "agent": "ActionComposer",
        "shipment_id": shipment_id,
        "proposed_action": {
            "header": f"Autonomous reroute for {shipment_id}",
            "driver_sms_draft": driver_msg,
            "customer_email_draft": customer_msg,
            "recommended_option": "APPROVE_REROUTE",
            "decision_options": decision_options,
        },
    }

    state.notifications.append(
        {
            "id": f"NTF-{uuid.uuid4().hex[:6].upper()}",
            "shipment_id": shipment_id,
            "channel": "system",
            "message": customer_msg,
            "created_at": int(time.time()),
        }
    )
    state.notifications.append(
        {
            "id": f"NTF-{uuid.uuid4().hex[:6].upper()}",
            "shipment_id": shipment_id,
            "channel": "seller",
            "message": f"Seller alert: hazard detected for {shipment_id}. AI recommends reroute.",
            "created_at": int(time.time()),
        }
    )
    state.notifications.append(
        {
            "id": f"NTF-{uuid.uuid4().hex[:6].upper()}",
            "shipment_id": shipment_id,
            "channel": "receiver",
            "message": f"Receiver alert: shipment {shipment_id} may incur delay while mitigation is applied.",
            "created_at": int(time.time()),
        }
    )

    ontology_graph.update_shipment_position(shipment_id, current_lat, current_lon)
    ontology_graph.update_shipment_route(shipment_id, alt_route)

    logger.info(
        "Autonomous reroute applied",
        extra={
            "shipment_id": shipment_id,
            "disruption_id": disruption.get("id"),
            "predicted_delay": agent_result.get("predicted_delay", 0),
        },
    )
    return True


async def run_autonomous_monitor_cycle() -> int:
    """Silently monitor all active shipments and reroute when hazards intersect upcoming routes."""
    reroutes = 0
    now_ts = time.time()

    for shipment in state.shipments:
        monitoring_start_ts = float(shipment.get("monitoringStartTs", 0) or 0)
        if now_ts < monitoring_start_ts:
            continue

        for disruption in state.disruptions:
            if shipment.get("lastMitigatedDisruptionId") == disruption.get("id"):
                continue

            if _shipment_intersects_disruption(shipment, disruption):
                if _reroute_shipment_for_disruption(shipment, disruption):
                    reroutes += 1
                break

    if reroutes:
        state.active_payload = None
        await manager.broadcast_state()

    return reroutes


def _set_preview_risk_payload_if_needed() -> None:
    if state.active_payload is not None:
        return
    if not state.disruptions or not state.shipments:
        return

    disruption = state.disruptions[-1]
    scored_shipments = []
    for shipment in state.shipments:
        geo = _compute_geospatial_risk(shipment, disruption)
        scored_shipments.append((shipment, geo))

    scored_shipments.sort(
        key=lambda item: (
            item[0].get("source") == "seller_portal",
            float(item[0].get("createdAt", 0) or 0),
            item[1].get("final_risk_score", 0),
        ),
        reverse=True,
    )
    top = scored_shipments[0]
    shipment = top[0]
    geo = top[1]
    recommended_option = "APPROVE_REROUTE" if geo.get("final_risk_score", 0) >= 40 else "SAFE_WAIT"
    state.active_payload = {
        "agent": "ActionComposer",
        "shipment_id": shipment.get("id"),
        "proposed_action": {
            "header": f"Shipment {shipment.get('id')} impacted by {disruption.get('type', 'DISRUPTION')}",
            "driver_sms_draft": (
                f"Risk match detected. Overlap {geo.get('overlap_percent', 0.0)}%. "
                f"Recommended action: {recommended_option}."
            ),
            "customer_email_draft": (
                f"AI agent has evaluated shipment {shipment.get('id')} after a disruption signal. "
                f"Risk score {int(geo.get('final_risk_score', 0))}% based on overlap and urgency."
            ),
            "recommended_option": recommended_option,
            "decision_options": [
                {
                    "id": "reroute-now",
                    "label": "Approve Reroute",
                    "description": "Move to alternate route immediately",
                    "decision": "APPROVE_REROUTE",
                },
                {
                    "id": "safe-wait",
                    "label": "Safe Wait 30 Min",
                    "description": "Pause and re-evaluate after signal clears",
                    "decision": "SAFE_WAIT",
                },
                {
                    "id": "escalate",
                    "label": "Escalate to Dispatch",
                    "description": "Escalate to seller and dispatch control",
                    "decision": "ESCALATE",
                },
            ],
        },
    }
    state.notifications.append(
        {
            "id": f"NTF-{uuid.uuid4().hex[:6].upper()}",
            "shipment_id": shipment.get("id"),
            "channel": "system",
            "message": (
                f"AI prompt created for {shipment.get('id')}: overlap={geo.get('overlap_percent', 0.0)}%, "
                f"risk={int(geo.get('final_risk_score', 0))}%, recommendation={recommended_option}."
            ),
            "created_at": int(time.time()),
        }
    )

# WebSocket manager
class ConnectionManager:
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        state.connections.append(websocket)
        # Send initial state
        await self.broadcast_state()

    def disconnect(self, websocket: WebSocket):
        if websocket in state.connections:
            state.connections.remove(websocket)

    async def broadcast(self, message: dict):
        disconnected = []
        for connection in state.connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            if conn in state.connections:
                state.connections.remove(conn)

    async def broadcast_state(self):
        payload = {
            "type": "STATE_UPDATE",
            "shipments": state.shipments,
            "disruptions": state.disruptions,
            "activePayload": state.active_payload,
            "notifications": state.notifications[-50:],
        }
        await self.broadcast(payload)

manager = ConnectionManager()

@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/api/cities")
async def get_cities():
    """Return the list of city names supported for origin/destination routing."""
    return {"cities": list_known_cities()}

@app.get("/api/shipments")
async def get_shipments():
    """Return current shipments state."""
    return {"shipments": state.shipments}

@app.get("/api/disruptions")
async def get_disruptions():
    """Return current disruptions state."""
    return {"disruptions": state.disruptions}


@app.get("/api/state")
async def get_state():
    """Return full in-memory state snapshot for integration verification."""
    return {
        "shipments": state.shipments,
        "disruptions": state.disruptions,
        "activePayload": state.active_payload,
        "notifications": state.notifications[-50:],
    }


@app.get("/api/schedules")
async def get_schedules():
    """Return all scheduled shipments with monitoring start metadata."""
    schedules = []
    now_ts = time.time()
    for shp in state.shipments:
        details = shp.get("shipment_details", {})
        monitoring_ts = float(shp.get("monitoringStartTs", 0) or 0)
        schedules.append(
            {
                "shipment_id": shp.get("id"),
                "origin": details.get("origin", "Unknown"),
                "destination": details.get("destination", "Unknown"),
                "cargo": shp.get("cargo", "General Cargo"),
                "priority": shp.get("priority", "MEDIUM"),
                "monitoring_start_ts": monitoring_ts,
                "monitoring_starts_in_seconds": max(0, int(monitoring_ts - now_ts)),
                "risk_score": shp.get("riskScore", 0),
            }
        )
    return {"schedules": schedules}


@app.get("/api/notifications")
async def get_notifications():
    return {"notifications": state.notifications[-100:]}


@app.post("/api/shipments/{shipment_id}/gps")
async def update_truck_gps(
    shipment_id: str,
    request: GPSUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    shipment = next((s for s in state.shipments if s.get("id") == shipment_id), None)
    if shipment is None:
        return {"status": "error", "message": "shipment not found"}

    shipment["currentLat"] = float(request.lat)
    shipment["currentLon"] = float(request.lon)
    ontology_graph.update_shipment_position(shipment_id, float(request.lat), float(request.lon))
    await manager.broadcast_state()

    return {
        "status": "updated",
        "shipment_id": shipment_id,
        "lat": shipment["currentLat"],
        "lon": shipment["currentLon"],
        "source": request.source,
    }


@app.post("/api/shipments/{shipment_id}/notify")
async def notify_stakeholders(
    shipment_id: str,
    request: NotifyStakeholdersRequest,
    current_user: dict = Depends(get_current_user),
):
    shipment = next((s for s in state.shipments if s.get("id") == shipment_id), None)
    if shipment is None:
        return {"status": "error", "message": "shipment not found"}

    details = shipment.get("shipment_details", {})
    origin = details.get("origin", "origin")
    destination = details.get("destination", "destination")
    risk = shipment.get("riskScore", 0)
    base_note = (
        f"Shipment {shipment_id} ({origin} -> {destination}) update: risk={risk}%. {request.note}"
    )

    seller_msg = {
        "id": f"NTF-{uuid.uuid4().hex[:6].upper()}",
        "shipment_id": shipment_id,
        "channel": "seller",
        "to": request.seller_contact,
        "message": base_note,
        "created_at": int(time.time()),
    }
    receiver_msg = {
        "id": f"NTF-{uuid.uuid4().hex[:6].upper()}",
        "shipment_id": shipment_id,
        "channel": "receiver",
        "to": request.receiver_contact,
        "message": base_note,
        "created_at": int(time.time()),
    }
    state.notifications.extend([seller_msg, receiver_msg])

    return {
        "status": "sent",
        "shipment_id": shipment_id,
        "notifications": [seller_msg, receiver_msg],
    }


@app.post("/api/agent/decision")
async def submit_agent_decision(
    request: AgentDecisionRequest,
    current_user: dict = Depends(get_current_user),
):
    shipment = next((s for s in state.shipments if s.get("id") == request.shipment_id), None)
    if shipment is None:
        return {"status": "error", "message": "shipment not found"}

    decision = (request.decision or "").strip().upper()
    allowed = {"APPROVE", "REJECT", "APPROVE_REROUTE", "SAFE_WAIT", "ESCALATE"}
    if decision not in allowed:
        return {"status": "error", "message": "decision must be one of APPROVE, REJECT, APPROVE_REROUTE, SAFE_WAIT, ESCALATE"}

    if decision in {"REJECT", "SAFE_WAIT"}:
        shipment["riskScore"] = max(0, int(shipment.get("riskScore", 0)) - 10)
    elif decision in {"APPROVE", "APPROVE_REROUTE"}:
        shipment["riskScore"] = max(int(shipment.get("riskScore", 0)), 65)
    elif decision == "ESCALATE":
        shipment["riskScore"] = max(int(shipment.get("riskScore", 0)), 40)

    state.notifications.append(
        {
            "id": f"NTF-{uuid.uuid4().hex[:6].upper()}",
            "shipment_id": request.shipment_id,
            "channel": "control_tower",
            "message": f"Operator decision: {decision}",
            "created_at": int(time.time()),
        }
    )

    state.notifications.append(
        {
            "id": f"NTF-{uuid.uuid4().hex[:6].upper()}",
            "shipment_id": request.shipment_id,
            "channel": "seller",
            "message": f"Seller notified: AI decision for {request.shipment_id} is {decision}.",
            "created_at": int(time.time()),
        }
    )
    state.notifications.append(
        {
            "id": f"NTF-{uuid.uuid4().hex[:6].upper()}",
            "shipment_id": request.shipment_id,
            "channel": "receiver",
            "message": f"Receiver notified: shipment {request.shipment_id} status updated to {decision}.",
            "created_at": int(time.time()),
        }
    )
    state.active_payload = None
    await manager.broadcast_state()
    return {"status": "accepted", "shipment_id": request.shipment_id, "decision": decision}

@app.get("/api/ontology")
async def get_ontology():
    """Return the NetworkX ontology graph summary and active nodes."""
    return {
        "summary": ontology_graph.summary(),
        "shipments": ontology_graph.get_active_shipments(),
        "disruptions": ontology_graph.get_active_disruptions(),
    }


@app.post("/api/schedule-transport")
async def schedule_transport(
    request: ScheduleTransportRequest,
    current_user: dict = Depends(get_current_user),
):
    """Schedule a transport from point A to B and arm autonomous hazard monitoring."""
    origin = request.origin.strip()
    destination = request.destination.strip()
    if not origin or not destination:
        return {"status": "error", "message": "origin and destination are required"}

    # Validate both cities against the known coordinate map
    origin_coord = get_city_coords_or_none(origin)
    dest_coord = get_city_coords_or_none(destination)
    unknown = []
    if origin_coord is None:
        unknown.append(f"origin '{origin}'")
    if dest_coord is None:
        unknown.append(f"destination '{destination}'")
    if unknown:
        known = list_known_cities()
        return {
            "status": "error",
            "message": f"Unknown city: {', '.join(unknown)}. "
                       f"Please choose from the supported cities list.",
            "known_cities": known,
        }

    route = state.knowledge_model.fetch_osrm_route(origin_coord, dest_coord)

    shipment_id = f"SHP-{uuid.uuid4().hex[:6].upper()}"
    priority = _normalize_priority(request.priority)
    start_in_minutes = max(int(request.start_in_minutes), 0)
    monitoring_start_ts = time.time() + max(0, (start_in_minutes - AUTONOMOUS_CHECK_LEAD_MINUTES) * 60)

    shipment = {
        "id": shipment_id,
        "cargo": request.cargo,
        "priority": priority,
        "currentRoute": route,
        "currentLat": origin_coord[0],
        "currentLon": origin_coord[1],
        "riskScore": 0,
        "monitoringStartTs": monitoring_start_ts,
        "lastMitigatedDisruptionId": None,
        "createdAt": time.time(),
        "source": f"{current_user.get('role', 'unknown')}_portal",
        "created_by": current_user.get("sub", "unknown"),
        "shipment_details": {
            "shipment_id": shipment_id,
            "origin": origin,
            "destination": destination,
            "priority": priority,
            "priority_score": _priority_score(priority),
            "mode": "road",
            "fuel_rate": 2.6,
            "penalty_rate": 150.0,
            "remaining_distance_km": 500.0,
            "original_eta_hours": 12.0,
            "base_fuel_distance_km": 500.0,
        },
    }

    state.shipments.append(shipment)
    ontology_graph.add_shipment(shipment)
    await manager.broadcast_state()

    return {
        "status": "scheduled",
        "shipment": shipment,
        "monitoring_starts_in_minutes": max(0, start_in_minutes - AUTONOMOUS_CHECK_LEAD_MINUTES),
    }

_SIGNAL_SCENARIOS: Dict[str, Dict[str, Any]] = {
    "weather": {
        "source": "demo_weather",
        "raw_text": "Severe cyclonic storm Biparjoy making landfall near Gujarat coast. "
                    "Port of Mundra suspended operations. Highways NH-47 and NH-954 closed.",
        "location": "Ahmedabad",
        "lat": 23.0225,
        "lon": 72.5714,
        "event_type": "cyclone",
        "severity": 9,
    },
    "port_congestion": {
        "source": "demo_port",
        "raw_text": "JNPT Mumbai reports 4-day backlog due to crane failure and labour strike. "
                    "Container dwell time exceeding 14 days. 60 vessels at anchorage.",
        "location": "Mumbai",
        "lat": 18.9500,
        "lon": 72.9354,
        "event_type": "port_congestion",
        "severity": 7,
    },
    "road_closure": {
        "source": "demo_road",
        "raw_text": "National Highway NH-44 blocked near Nagpur due to massive pile-up. "
                    "Police advise 6-hour minimum delay. Alternative route via NH-161 available.",
        "location": "Nagpur",
        "lat": 21.1458,
        "lon": 79.0882,
        "event_type": "road_closure",
        "severity": 6,
    },
    "customs_delay": {
        "source": "demo_customs",
        "raw_text": "Delhi Air Cargo Complex ISCBF conducting enhanced inspection on all pharma shipments. "
                    "Clearance times extended to 72 hours. Cold-chain SLA breach risk high.",
        "location": "Delhi",
        "lat": 28.6139,
        "lon": 77.2090,
        "event_type": "customs_delay",
        "severity": 5,
    },
    "civil_unrest": {
        "source": "demo_civil",
        "raw_text": "Widespread protests blocking logistics hubs across Kolkata. "
                    "NH-12 and NH-16 entry ramps closed. Rail freight services suspended until further notice.",
        "location": "Kolkata",
        "lat": 22.5726,
        "lon": 88.3639,
        "event_type": "civil_unrest",
        "severity": 8,
    },
}

_DEFAULT_SIGNAL = {
    "source": "manual_demo",
    "raw_text": "Heavy flooding and highway closure risk near Chennai logistics corridor",
    "location": "Chennai",
    "lat": 13.0827,
    "lon": 80.2707,
    "event_type": "flooding",
    "severity": 8,
}


@app.post("/api/inject-signal")
async def inject_signal(
    body: SignalInjectRequest = SignalInjectRequest(),
    current_user: dict = Depends(get_current_user),
):
    """
    Trigger the full 5-layer pipeline on demand with an optional signal type.
    signal_type: auto | weather | port_congestion | road_closure | customs_delay | civil_unrest
    1. Layer 1 — Ingest signals (real APIs if auto, else synthetic scenario)
    2. Publish to Kafka-lite event stream
    3. Layer 2 — LlamaIndex RAG extracts DisruptionObjects
    4. Layer 3 — Ontology graph adds DisruptionZone
    5. Layer 4 — LangGraph AI agents (RiskAnalyst → RouteOptimizer → ActionComposer)
    6. Broadcast results via WebSocket to Cesium frontend
    """
    try:
        logger.info(f"Signal injection triggered — type={body.signal_type} by {current_user.get('sub')}")

        # ── Layer 1: signal selection ────────────────────────────────────────
        if body.signal_type in _SIGNAL_SCENARIOS:
            raw_signals = [_SIGNAL_SCENARIOS[body.signal_type]]
            logger.info(f"Using synthetic scenario: {body.signal_type}")
        else:
            # "auto" — try real API ingestion
            raw_signals = await fetch_all_signals()
            if not raw_signals:
                raw_signals = [_DEFAULT_SIGNAL]

        # Publish each to the Kafka-lite event stream
        for sig in raw_signals:
            await event_stream.publish(sig)

        disruptions_added = 0

        # ── Layer 2: LlamaIndex RAG → DisruptionObject ────────────────────────
        for raw_signal in raw_signals:
            disruption_data = rag_processor.extract(raw_signal)
            if disruption_data is None:
                # RAG couldn't extract a disruption — try legacy rule-based processor
                disruption_data = state.processor.process_signal(raw_signal)

            before_count = len(state.disruptions)
            _ensure_disruption(disruption_data)
            if len(state.disruptions) > before_count:
                disruptions_added += 1
        
        reroutes = await run_autonomous_monitor_cycle()
        _set_preview_risk_payload_if_needed()
        await manager.broadcast_state()
        return {
            "status": "success",
            "signals_processed": len(raw_signals),
            "disruptions_added": disruptions_added,
            "reroutes_applied": reroutes,
        }
        
    except Exception as e:
        logger.error(f"Error in manual injection: {e}")
        return {"status": "error", "message": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.info(f"Received from client: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

async def simulation_loop():
    """
    Background task — full 5-layer pipeline runs every 30 seconds.
    Layer 1: real API ingestion (GDELT, Open-Meteo, MapmyIndia, GoComet)
    Layer 2: LlamaIndex RAG → DisruptionObject
    Layer 3: ontology graph auto-triggers intersection query
    Layer 4: LangGraph AI agents generate recommendations
    Layer 5: WebSocket broadcast to Cesium frontend
    """
    
    # Wait to allow system to start up before looping
    await asyncio.sleep(2)

    while True:
        try:
            logger.info("Simulation cycle: fetching signals from real APIs...")

            # ── Layer 1: real API ingestion ──────────────────────────────────
            raw_signals = await fetch_all_signals()

            # Publish to Kafka-lite event stream
            for sig in raw_signals:
                await event_stream.publish(sig)

            for raw_signal in raw_signals:
                # ── Layer 2: LlamaIndex RAG → DisruptionObject ───────────────
                disruption_data = rag_processor.extract(raw_signal)
                if disruption_data is None:
                    disruption_data = state.processor.process_signal(raw_signal)

                _ensure_disruption(disruption_data)

            reroutes = await run_autonomous_monitor_cycle()
            if reroutes:
                logger.info(f"Autonomous monitor applied {reroutes} reroute(s)")
            
            # Auto-animate trucks along their route for the demo
            moved = False
            for shipment in state.shipments:
                route = shipment.get("currentRoute", [])
                if len(route) > 1:
                    # Move truck to the next point in the route (simulate movement)
                    # Pop the first coordinate and set current to it
                    current_pt = route.pop(0)
                    shipment["currentLon"], shipment["currentLat"] = current_pt[0], current_pt[1]
                    ontology_graph.update_shipment_position(shipment.get("id"), current_pt[1], current_pt[0])
                    moved = True
            
            if moved:
                await manager.broadcast_state()

            # Wait before next cycle
            await asyncio.sleep(5)
            
            await manager.broadcast_state()
            
        except Exception as e:
            logger.error(f"Error in simulation loop: {e}")
            
        await asyncio.sleep(SIGNAL_POLL_INTERVAL_SECONDS)

@app.on_event("startup")
async def startup_event():
    # Connect event stream (Redis if available, otherwise asyncio.Queue)
    await event_stream.try_connect_redis()
    logger.info(f"Event stream backend: {event_stream.backend}")
    # Start simulation loop (polls real APIs every 30 s)
    asyncio.create_task(simulation_loop())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
