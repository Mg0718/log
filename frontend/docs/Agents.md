# LogosGotham: Frontend Agent Contracts & UI Guidelines

This repository contains the frontend for **LogosGotham**, a Palantir-inspired real-time logistics disruption intelligence system. It is a Next.js (App Router) application that provides a military-grade, 3D tactical command center using CesiumJS. It serves as the visual interface for backend AI Agents (LangGraph) that compute supply chain risks.

## 1. Getting Started

Install dependencies and run the development app:

```bash
npm install
npm run dev
Required Environment Variables:
You must have the following in your .env.local for the 3D globe to render:

NEXT_PUBLIC_CESIUM_ION_TOKEN (For Cesium base terrain)

NEXT_PUBLIC_GOOGLE_MAPS_API_KEY (For Google Map 3D Photorealistic Tiles)

2. Style & Aesthetic (The "Command Center" Vibe)
This application must not look like a standard SaaS dashboard. It must look like a secure, tactical military interface.

Backgrounds: Deep void blacks (#050505) and dark gunmetal (#0A0A0A).

Primary Accents: Tactical Cyan/Teal (#00F0FF) and Radar Green (#00FF41).

Alert Colors: Hazard Amber (#FFB000) and Critical Red (#FF003C).

Typography: - MUST use monospace fonts (Space Mono, JetBrains Mono, or Geist Mono) for all telemetry, coordinates, agent logs, and numbers.

Headers should be UPPERCASE with wide letter-spacing (tracking-widest).

CSS Effects: Implement a global .crt-overlay class to provide faint scanlines and a dark vignette over the entire application.

Borders & Shadows: Disable soft CSS shadows. Use hard, 1px solid borders (border-cyan-900/40) with sharp or chamfered corners.

3. Architecture & Code Standards
Strict TypeScript: Avoid any. Use the explicit interfaces defined in Section 5.

State Management: Use Zustand for global state (useLogisticsStore). Do not use React Context or prop-drilling for core data (Shipments, Disruptions, Active Alerts).

Cesium Isolation: CesiumJS is extremely heavy. Wrap the viewer initialization in a useRef and useEffect block. Never trigger full React component re-renders on the Cesium container when simulated vehicle coordinates update.

Layout Structure: The main view must be a full-screen CSS Grid divided into:

LeftPanel: Data Layer Toggles (News, Weather, Ports).

CenterMap: The full-bleed CesiumJS 3D Globe.

RightHUD: The Agent Telemetry Readout and Action Prompts.

4. Shadcn/UI Implementation
The interface utilizes shadcn/ui components, heavily customized for the dark-mode tactical theme.

Place generated files under src/components/ui.

Use React.forwardRef with the cn() utility for class names.

Modify globals.css to force the Shadcn "background" variable to #050505 and "primary" to our Tactical Cyan.

Shadcn Cards, Dialogs, and Buttons must be styled to look like rigid, glassmorphic tactical panels.

5. Agent Data Contracts (IPC / API Payloads)
The frontend does not compute risk; it renders the "thoughts" of the backend AI agents. The UI must parse the following JSON structures (via WebSocket or polling) and update the Zustand store.

TypeScript Interfaces

TypeScript
export type Coordinate = [number, number]; // [longitude, latitude]

export interface Shipment {
  id: string;
  cargo: string;
  priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  currentRoute: Coordinate[];
  riskScore: number;
}

export interface DisruptionEvent {
  id: string;
  type: "FLOOD" | "PORT_CONGESTION" | "HIGHWAY_CLOSURE";
  polygonGeoJSON: Coordinate[][]; // For rendering the 3D hazard volume
  severity: number;
}
Agent 1: RiskAnalyst Payload

Triggered when: A new disruption occurs.
UI Action: Flash a warning HUD. Turn specific shipment route lines on the Cesium map from Green to Amber/Red.

JSON
{
  "agent": "RiskAnalyst",
  "status": "complete",
  "event": {
    "id": "EVT-992",
    "type": "FLOOD",
    "polygonGeoJSON": [[[79.89, 12.71], [79.95, 12.71], [79.95, 12.80], [79.89, 12.71]]],
    "severity": 8.5
  },
  "affected_shipments": [
    {
      "shipment_id": "SHP-2847",
      "risk_score": 91,
      "severity": "CRITICAL",
      "reasoning_log": "78% route overlap with flooded NH-48. 6hr SLA window."
    }
  ]
}
Agent 2: RouteOptimizer Payload

Triggered when: The system calculates a detour for an at-risk shipment.
UI Action: Draw a new, glowing alternate path on the 3D globe branching off the original route.

JSON
{
  "agent": "RouteOptimizer",
  "shipment_id": "SHP-2847",
  "calculated_alternatives": [
    {
      "option_id": "OPT-A",
      "route_polyline": [[79.89, 12.71], [80.1, 13.0], [80.5, 13.2]], 
      "eta_delta_minutes": "+42",
      "cost_delta_inr": "+1200"
    }
  ]
}
Agent 3: ActionComposer Payload

Triggered when: The backend presents the final decision to the human dispatcher.
UI Action: Populate the RightHUD with a typewriter-effect display of the text, and render two large tactical buttons: [ APPROVE ] and [ REJECT ].

JSON
{
  "agent": "ActionComposer",
  "shipment_id": "SHP-2847",
  "proposed_action": {
    "header": "EXECUTE REROUTE VIA NH-77",
    "driver_sms_draft": "ALERT: NH-48 flooded. Reroute via NH-77. New ETA 20:00.",
    "customer_email_draft": "Proactive Alert: Shipment rerouted to avoid flood. SLA maintained."
  }
}
6. Cesium 3D Map Implementation Rules
Base Imagery: Initialize GoogleMaps3DTilesProvider to get photorealistic Indian highways and terrain.

Disruption Volumes: Render polygonGeoJSON data from Agent 1 as extruded 3D volumes (e.g., extrudedHeight: event.severity * 500). Use a semi-transparent colored material (e.g., Red for Highway Closure, Blue for Flood) so it looks like a glowing forcefield.

Live Telemetry Simulation: Create a VehicleTracker class that uses setInterval (ticking every 500ms) to move truck Billboards along their polyline coordinate arrays.

Cinematic Camera: When an agent flags a "CRITICAL" shipment, use viewer.camera.flyTo() to automatically pan, zoom, and tilt (-45 degree pitch) to center the intersecting hazard zone and the approaching truck.

7. Hackathon Execution Plan (Frontend)
Mock State First: Do not wait for the backend APIs. Create a mockData.ts file containing the exact JSON structures above. Build the entire UI using this static data.

The HUD Typewriter: Build the RightHUD component so that reasoning_log text appears character-by-character, simulating an AI "thinking" in real-time.

The "God Mode" Button: Implement a hidden "Inject Disruption" button. For the live demo, clicking this button should update the Zustand state with the Agent 1 payload, triggering all the map animations instantly.