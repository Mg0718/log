import { create } from 'zustand';

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
  polygonGeoJSON: Coordinate[][];
  severity: number;
}

export interface AffectedShipment {
  shipment_id: string;
  risk_score: number;
  severity: string;
  reasoning_log: string;
}

export interface RiskAnalystPayload {
  agent: "RiskAnalyst";
  status: "complete";
  event: DisruptionEvent;
  affected_shipments: AffectedShipment[];
}

export interface RouteAlternative {
  option_id: string;
  route_polyline: Coordinate[];
  eta_delta_minutes: string;
  cost_delta_inr: string;
}

export interface RouteOptimizerPayload {
  agent: "RouteOptimizer";
  shipment_id: string;
  calculated_alternatives: RouteAlternative[];
}

export interface ActionComposerPayload {
  agent: "ActionComposer";
  shipment_id: string;
  proposed_action: {
    header: string;
    driver_sms_draft: string;
    customer_email_draft: string;
  };
}

export type AgentPayload = RiskAnalystPayload | RouteOptimizerPayload | ActionComposerPayload | null;

interface LogisticsState {
  shipments: Shipment[];
  disruptions: DisruptionEvent[];
  activePayload: AgentPayload;
  layers: {
    news: boolean;
    weather: boolean;
    ports: boolean;
    shipments: boolean;
  };
  
  // Actions
  setShipments: (shipments: Shipment[]) => void;
  addDisruption: (disruption: DisruptionEvent) => void;
  setActivePayload: (payload: AgentPayload) => void;
  toggleLayer: (layer: keyof LogisticsState['layers']) => void;
  injectDemoSignal: () => void;
}

export const useLogisticsStore = create<LogisticsState>((set) => ({
  shipments: [
    {
      id: "SHP-2847",
      cargo: "High-Precision Sensors",
      priority: "CRITICAL",
      currentRoute: [
        [79.89, 12.71],
        [80.0, 12.9],
        [80.2, 13.1],
      ],
      riskScore: 15,
    },
  ],
  disruptions: [],
  activePayload: null,
  layers: {
    news: true,
    weather: false,
    ports: true,
    shipments: true,
  },

  setShipments: (shipments) => set({ shipments }),
  addDisruption: (disruption) => set((state) => ({ 
    disruptions: [...state.disruptions, disruption] 
  })),
  setActivePayload: (payload) => set({ activePayload: payload }),
  toggleLayer: (layer) => set((state) => ({
    layers: { ...state.layers, [layer]: !state.layers[layer] }
  })),
  
  injectDemoSignal: () => {
    const demoPayload: RiskAnalystPayload = {
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
    };
    
    set((state) => ({
      activePayload: demoPayload,
      disruptions: [...state.disruptions, demoPayload.event],
      shipments: state.shipments.map(s => 
        s.id === "SHP-2847" ? { ...s, riskScore: 91 } : s
      )
    }));
    
    // Simulate Route Optimizer kick-in after 3 seconds
    setTimeout(() => {
        const routePayload: RouteOptimizerPayload = {
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
        };
        set({ activePayload: routePayload });
    }, 3000);

    // Simulate Action Composer kick-in after 6 seconds
    setTimeout(() => {
        const actionPayload: ActionComposerPayload = {
            "agent": "ActionComposer",
            "shipment_id": "SHP-2847",
            "proposed_action": {
              "header": "EXECUTE REROUTE VIA NH-77",
              "driver_sms_draft": "ALERT: NH-48 flooded. Reroute via NH-77. New ETA 20:00.",
              "customer_email_draft": "Proactive Alert: Shipment rerouted to avoid flood. SLA maintained."
            }
        };
        set({ activePayload: actionPayload });
    }, 6000);
  }
}));
