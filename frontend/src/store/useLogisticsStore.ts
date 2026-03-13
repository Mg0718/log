import { create } from 'zustand';
import { getAuthHeaders } from '@/store/useAuthStore';

export type Coordinate = [number, number]; // [longitude, latitude]

export interface Shipment {
  id: string;
  cargo: string;
  priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  currentRoute: Coordinate[];
  riskScore: number;
  // Real GPS position of the truck (origin city coordinates from backend)
  currentLat?: number;
  currentLon?: number;
  monitoringStartTs?: number;
  lastMitigatedDisruptionId?: string | null;
}

export interface ScheduleTransportInput {
  origin: string;
  destination: string;
  cargo: string;
  priority: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  start_in_minutes: number;
}

export interface DisruptionEvent {
  id: string;
  type: "FLOOD" | "PORT_CONGESTION" | "HIGHWAY_CLOSURE" | "FLOODING" | "CYCLONE";
  polygonGeoJSON: Coordinate[][];
  severity: number;
}

export interface AffectedShipment {
  shipment_id: string;
  risk_score: number;
  severity: string;
  reasoning_log: string;
}

export interface AgentDecisionOption {
  id: string;
  label: string;
  description: string;
  decision: "APPROVE_REROUTE" | "SAFE_WAIT" | "ESCALATE" | "APPROVE" | "REJECT";
}

export interface NotificationItem {
  id: string;
  shipment_id: string;
  channel: string;
  message: string;
  created_at: number;
  to?: string;
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
    recommended_option?: string;
    decision_options?: AgentDecisionOption[];
  };
}

export type AgentPayload = RiskAnalystPayload | RouteOptimizerPayload | ActionComposerPayload | null;

interface LogisticsState {
  shipments: Shipment[];
  disruptions: DisruptionEvent[];
  activePayload: AgentPayload;
  notifications: NotificationItem[];
  isInjecting: boolean;
  systemMessage: string;
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
  setNotifications: (notifications: NotificationItem[]) => void;
  toggleLayer: (layer: keyof LogisticsState['layers']) => void;
  injectDemoSignal: (signalType?: string) => void;
  scheduleTransport: (payload: ScheduleTransportInput) => Promise<Record<string, unknown>>;
  updateTruckGps: (shipmentId: string, lat: number, lon: number) => Promise<void>;
  notifyStakeholders: (shipmentId: string) => Promise<void>;
  sendAgentDecision: (shipmentId: string, decision: "APPROVE" | "REJECT") => Promise<void>;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const useLogisticsStore = create<LogisticsState>((set, get) => ({
  shipments: [],
  disruptions: [],
  activePayload: null,
  notifications: [],
  isInjecting: false,
  systemMessage: "",
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
  setNotifications: (notifications) => set({ notifications }),
  toggleLayer: (layer) => set((state) => ({
    layers: { ...state.layers, [layer]: !state.layers[layer] }
  })),
  
  injectDemoSignal: async (signalType = 'auto') => {
    if (get().isInjecting) return; // Prevent double-clicks
    set({ isInjecting: true });
    
    try {
      const response = await fetch(`${API_URL}/api/inject-signal`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ signal_type: signalType }),
      });
      
      if (!response.ok) {
        console.error('Inject signal failed:', response.statusText);
      } else {
        const data = await response.json();
        console.log('Signal injected:', data);
      }
    } catch (error) {
      console.error('Failed to inject signal:', error);
      // Fallback: run local demo if backend is unavailable
      const demoPayload: RiskAnalystPayload = {
        agent: "RiskAnalyst",
        status: "complete",
        event: {
          id: "EVT-LOCAL",
          type: "FLOOD",
          polygonGeoJSON: [[[79.89, 12.71], [79.95, 12.71], [79.95, 12.80], [79.89, 12.71]]],
          severity: 8.5
        },
        affected_shipments: [
          {
            shipment_id: "SHP-DEMO",
            risk_score: 91,
            severity: "CRITICAL",
            reasoning_log: "78% route overlap with flooded NH-48. 6hr SLA window. (LOCAL FALLBACK)"
          }
        ]
      };
      set((state) => ({
        activePayload: demoPayload,
        disruptions: [...state.disruptions, demoPayload.event],
      }));
    } finally {
      set({ isInjecting: false });
    }
  },

  scheduleTransport: async (payload) => {
    try {
      const response = await fetch(`${API_URL}/api/schedule-transport`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      if (data.status === "error") {
        set({ systemMessage: data.message || "Failed to schedule transport" });
        return data;
      }
      if (!response.ok) {
        const msg = data.message || "Failed to schedule transport";
        set({ systemMessage: msg });
        return { status: "error", message: msg };
      }

      set({
        systemMessage: `Scheduled ${data.shipment.id} (${payload.origin} -> ${payload.destination})`,
      });
      return data;
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Schedule failed";
      set({ systemMessage: msg });
      return { status: "error", message: msg };
    }
  },

  updateTruckGps: async (shipmentId, lat, lon) => {
    try {
      const response = await fetch(`${API_URL}/api/shipments/${shipmentId}/gps`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ lat, lon, source: "frontend-operator" }),
      });
      const data = await response.json();
      if (!response.ok || data.status === "error") {
        throw new Error(data.message || "GPS update failed");
      }
      set({ systemMessage: `GPS updated for ${shipmentId}` });
    } catch (error) {
      const msg = error instanceof Error ? error.message : "GPS update failed";
      set({ systemMessage: msg });
    }
  },

  notifyStakeholders: async (shipmentId) => {
    try {
      const response = await fetch(`${API_URL}/api/shipments/${shipmentId}/notify`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({
          seller_contact: "seller@logogotham.ai",
          receiver_contact: "receiver@logogotham.ai",
          note: "AI reroute and ETA update issued",
        }),
      });
      const data = await response.json();
      if (!response.ok || data.status === "error") {
        throw new Error(data.message || "Notification failed");
      }
      set({ systemMessage: `Notified seller + receiver for ${shipmentId}` });
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Notification failed";
      set({ systemMessage: msg });
    }
  },

  sendAgentDecision: async (shipmentId, decision) => {
    try {
      const response = await fetch(`${API_URL}/api/agent/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeaders() },
        body: JSON.stringify({ shipment_id: shipmentId, decision }),
      });
      const data = await response.json();
      if (!response.ok || data.status === "error") {
        throw new Error(data.message || "Decision submission failed");
      }
      set({ systemMessage: `Decision ${decision} recorded for ${shipmentId}` });
    } catch (error) {
      const msg = error instanceof Error ? error.message : "Decision submission failed";
      set({ systemMessage: msg });
    }
  },
}));
