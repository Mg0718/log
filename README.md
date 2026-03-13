# LogosGotham — Proactive Logistics Intelligence Platform

## Problem Statement

India's logistics network moves millions of shipments daily across road corridors that are routinely disrupted by weather events, infrastructure failures, traffic incidents, and civil unrest. Current Transportation Management Systems (TMS) are **reactive**: dispatchers learn about a disruption only after a truck is already stuck, a delivery has missed its window, or a warehouse has been left idle. There is no mechanism to:

- **Detect** that a cyclone, road closure, or flooding event intersects a specific active route before the truck arrives.
- **Quantify** the cost impact of rerouting versus waiting out the disruption.
- **Act** at scale — a human dispatcher cannot simultaneously monitor dozens of live shipments against a constantly changing environmental threat landscape.

The result is delayed deliveries, elevated fuel costs from ad-hoc detours, strained buyer–seller relationships, and no audit trail of why a reroute decision was made.

## Solution

**LogosGotham** shifts logistics operations from reactive tracking to **proactive disruption management** through a five-layer AI pipeline:

| Layer | What it does |
|---|---|
| **Signal Ingestion** | Continuously polls Open-Meteo weather, NewsAPI, and MapmyIndia infrastructure feeds every 5 minutes, normalising raw data into a unified signal queue. |
| **RAG Signal Processor** | Uses Groq API (Llama 3) to parse unstructured text alerts into structured `DisruptionObject` schemas — extracting geospatial boundaries, severity, disruption type, and duration. |
| **Ontology Engine** | Maintains a live in-memory graph (NetworkX) as a **digital twin** of every active shipment, its current route waypoints, and all known hazard zones — the single source of truth for the platform. |
| **Geospatial Reasoning Engine** | Runs Shapely spatial-intersection analysis across a 15 km lookahead window on every route segment, flagging shipments whose path crosses a hazard zone before the truck arrives. |
| **Agentic Reasoning Engine** | A three-agent LangGraph state machine — **RiskAnalyst** scores route-hazard conflicts, **RouteOptimizer** calculates alternative OSRM detours with cost/time deltas, and **ActionComposer** drafts a human-readable reroute recommendation — all without waiting for human input. |

The output surfaces through an **Intelligence Map** — a real-time 3D CesiumJS dashboard — where:

- **Admins** see live shipment positions, active disruption zones, and AI-generated reroute proposals with cost breakdowns, and can **approve or reject** with one click (the approved route is instantly applied to the digital twin and broadcast to all connected clients).
- **Sellers** are notified when one of their shipments is at risk and can see the agent's recommended action.
- **Receivers** get live status updates when a reroute is approved, including the revised ETA.

### Key Outcomes

- **Proactive**: Disruptions are detected *before* the truck reaches the hazard zone.
- **Cost-aware**: Every reroute recommendation includes fuel cost delta and time penalty so the dispatcher can make an informed decision.
- **Role-gated**: Only admins can trigger simulations or approve reroutes; sellers and receivers get read-only visibility appropriate to their role.
- **Auditable**: Every agent decision, signal event, and operator action flows through a structured event log broadcast over WebSocket.

## Tech Stack

- **Backend**: Python · FastAPI · LangGraph · LlamaIndex (BM25 retrieval) · NetworkX · Shapely · Groq API (Llama 3)
- **Frontend**: Next.js 15 · TypeScript · Zustand · CesiumJS (3D globe) · Tailwind CSS · shadcn/ui
- **Routing**: OSRM public API for real road-network detour calculation
- **Auth**: JWT-based RBAC (Admin / Seller / Receiver demo users)

## Quick Start

```bash
# Clone and enter the repo
git clone https://github.com/Mg0718/log.git
cd log

# Start backend + frontend together
chmod +x run-all.sh
./run-all.sh
```

Or manually:

```bash
# Backend (Python 3.11+)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload

# Frontend (Node 18+)
cd frontend && npm install && npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Log in as:

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Seller | `seller` | `seller123` |
| Receiver | `receiver` | `receiver123` |

