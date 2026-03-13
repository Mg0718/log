"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { DataLayersPanel } from "@/components/DataLayersPanel";
import { AgentHUD } from "@/components/AgentHUD";
import { useLogisticsStore } from "@/store/useLogisticsStore";
import { useAuthStore } from "@/store/useAuthStore";
import { Package, ShoppingCart } from "lucide-react";

// Dynamically import the Cesium Map component to disable SSR
const LogosGothamMap = dynamic(() => import("@/components/LogosGothamMap"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full bg-[#050505] flex items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="w-12 h-12 border-2 border-cyan-500/20 border-t-cyan-500 rounded-full animate-spin" />
        <div className="text-[10px] text-cyan-500 font-bold uppercase tracking-[0.3em]">Initialising 3D Viewport...</div>
      </div>
    </div>
  ),
});

const WS_URL = process.env.NEXT_PUBLIC_API_URL
  ? process.env.NEXT_PUBLIC_API_URL.replace(/^http/, "ws") + "/ws"
  : "ws://localhost:8000/ws";

const RECONNECT_INTERVAL = 5000; // 5 seconds

export default function Home() {
  const { setShipments, setActivePayload, setNotifications } = useLogisticsStore();
  const { token, role, fullName } = useAuthStore();
  const [wsConnected, setWsConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const reconnectRef = useRef<() => void>(() => {});
  const router = useRouter();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!token) {
      router.replace("/login");
    }
  }, [token, router]);

  const connect = useCallback(() => {
    // Don't reconnect if unmounted or not authenticated
    if (!mountedRef.current) return;
    if (!token) return;

    // Clean up any existing socket
    if (socketRef.current) {
      socketRef.current.onopen = null;
      socketRef.current.onmessage = null;
      socketRef.current.onclose = null;
      socketRef.current.onerror = null;
      if (socketRef.current.readyState === WebSocket.OPEN || socketRef.current.readyState === WebSocket.CONNECTING) {
        socketRef.current.close();
      }
    }

    console.log("[WS] Connecting to", WS_URL);
    const socket = new WebSocket(WS_URL);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log("[WS] Connected");
      setWsConnected(true);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "STATE_UPDATE") {
          setShipments(data.shipments || []);
          useLogisticsStore.setState({ disruptions: data.disruptions || [] });
          setActivePayload(data.activePayload || null);
          setNotifications(data.notifications || []);
        }
      } catch (err) {
        console.error("[WS] Parse error:", err);
      }
    };

    socket.onclose = () => {
      console.log("[WS] Disconnected");
      setWsConnected(false);

      // Auto-reconnect only when still authenticated and mounted
      if (mountedRef.current && token) {
        console.log(`[WS] Reconnecting in ${RECONNECT_INTERVAL / 1000}s...`);
        reconnectTimerRef.current = setTimeout(() => {
          reconnectRef.current();
        }, RECONNECT_INTERVAL);
      }
    };

    socket.onerror = (error) => {
      console.error("[WS] Error:", error);
      // onclose will fire after onerror, triggering reconnect
    };
  }, [setShipments, setActivePayload, setNotifications]);

  useEffect(() => {
    reconnectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    mountedRef.current = true;
    if (token) {
      connect();
    }

    return () => {
      mountedRef.current = false;
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }
      if (socketRef.current) {
        socketRef.current.onclose = null; // Prevent reconnect on intentional close
        socketRef.current.close();
      }
    };
  }, [connect, token]);

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-black p-2 gap-2">
      {/* Guard: don't render UI until authenticated */}
      {!token ? null : (
        <>
      {/* LEFT PANEL */}
      <DataLayersPanel />

      {/* CENTER MAP AREA */}
      <div className="flex-1 relative glass-panel overflow-hidden">
        <LogosGothamMap />
        
        {/* Top Floating HUD bar */}
        <div className="absolute top-0 left-0 w-full p-4 flex justify-between items-start pointer-events-none z-10">
            <div className="flex flex-col gap-1">
                <h1 className="text-sm font-bold tracking-[0.4em] text-white uppercase bg-black/80 px-4 py-2 border-l-2 border-cyan-500">
                    LOGOS GOTHAM <span className="text-cyan-500 ml-2 font-mono">v1.2.0</span>
                </h1>
                <div className="text-[9px] text-cyan-900 font-bold tracking-widest px-4">
                    CLASSIFIED // NOFORN // GEN-AI HACKATHON
                </div>
            </div>

            <div className="flex items-center gap-4">
                {/* Role badge */}
                <div className={`bg-black/80 border px-3 py-1 flex items-center gap-2 ${role === "seller" ? "border-cyan-900/40" : "border-purple-900/40"}`}>
                    {role === "seller"
                      ? <Package className="w-3 h-3 text-cyan-500" />
                      : <ShoppingCart className="w-3 h-3 text-purple-400" />
                    }
                    <div className="flex flex-col">
                      <div className="text-[8px] text-zinc-500 uppercase font-bold">
                        {role === "seller" ? "Seller" : "Buyer"}
                      </div>
                      <div className={`text-[10px] font-bold uppercase ${role === "seller" ? "text-cyan-400" : "text-purple-400"}`}>
                        {fullName || role}
                      </div>
                    </div>
                </div>
                <div className="bg-black/80 border border-cyan-900/40 px-3 py-1 flex flex-col items-end">
                    <div className="text-[8px] text-zinc-500 uppercase font-bold">Network Status</div>
                    <div className="text-[10px] text-cyan-400 font-bold uppercase flex items-center gap-2">
                        <div className={`w-1 h-1 rounded-full ${wsConnected ? 'bg-cyan-400 animate-ping' : 'bg-red-500'}`} />
                        {wsConnected ? 'Encrypted' : 'Reconnecting...'}
                    </div>
                </div>
                <div className="bg-black/80 border border-cyan-900/40 px-3 py-1 flex flex-col items-end">
                    <div className="text-[8px] text-zinc-500 uppercase font-bold">System Load</div>
                    <div className="text-[10px] text-green-500 font-bold uppercase">4.2%</div>
                </div>
            </div>
        </div>
      </div>

      {/* RIGHT PANEL */}
      <AgentHUD />
        </>
      )}
    </div>
  );
}
