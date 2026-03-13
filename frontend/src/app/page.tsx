"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { DataLayersPanel } from "@/components/DataLayersPanel";
import { AgentHUD } from "@/components/AgentHUD";
import { useLogisticsStore } from "@/store/useLogisticsStore";
import { useAuthStore } from "@/store/useAuthStore";
import { Package, ShoppingCart, ShieldCheck } from "lucide-react";

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
  const intentionalCloseRef = useRef(new WeakSet<WebSocket>());
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);
  const reconnectRef = useRef<() => void>(() => {});
  const router = useRouter();
  const isAdmin = role === "admin";
  const isSeller = role === "seller";

  const hardRedirectToLogin = useCallback(() => {
    if (typeof window === "undefined") return;
    // Full navigation avoids stale in-memory chunk references during dev HMR.
    window.location.replace(`/login?ts=${Date.now()}`);
  }, []);

  // Redirect to login if not authenticated
  useEffect(() => {
    if (!token) {
      try {
        router.replace("/login");
      } catch {
        hardRedirectToLogin();
      }
    }
  }, [token, router, hardRedirectToLogin]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const onError = (event: ErrorEvent) => {
      const message = String(event?.message || "");
      const fileName = String(event?.filename || "");
      const isChunkLoadError =
        message.includes("ChunkLoadError") ||
        fileName.includes("/_next/static/chunks/");

      if (isChunkLoadError) {
        hardRedirectToLogin();
      }
    };

    window.addEventListener("error", onError);
    return () => window.removeEventListener("error", onError);
  }, [hardRedirectToLogin]);

  const closeSocket = useCallback((socket: WebSocket | null, intentional: boolean) => {
    if (!socket) return;
    if (intentional) {
      intentionalCloseRef.current.add(socket);
    }
    // Always silence message/error events immediately.
    socket.onmessage = null;
    socket.onerror = null;
    if (socket.readyState === WebSocket.OPEN) {
      // Clean close for an open connection.
      socket.onopen = null;
      socket.onclose = null;
      socket.close();
    } else if (socket.readyState === WebSocket.CONNECTING) {
      // NEVER call .close() on a CONNECTING socket — browsers emit
      // "WebSocket is closed before the connection is established" warning.
      // Instead let it finish connecting, then close it silently in onopen.
      socket.onopen = () => { socket.close(); };
      socket.onclose = null;
    } else {
      // CLOSING or CLOSED — nothing to do.
      socket.onopen = null;
      socket.onclose = null;
    }
  }, []);

  const connect = useCallback(() => {
    // Don't reconnect if unmounted or not authenticated
    if (!mountedRef.current) return;
    if (!token) return;

    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }

    // Clean up any existing socket
    if (socketRef.current) {
      closeSocket(socketRef.current, true);
      socketRef.current = null;
    }

    console.log("[WS] Connecting to", WS_URL);
    const socket = new WebSocket(WS_URL);
    socketRef.current = socket;

    socket.onopen = () => {
      if (socketRef.current !== socket) return;
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
      const intentional = intentionalCloseRef.current.has(socket);
      intentionalCloseRef.current.delete(socket);

      if (socketRef.current === socket) {
        socketRef.current = null;
      }

      if (intentional || !mountedRef.current) {
        return;
      }

      console.log("[WS] Disconnected");
      setWsConnected(false);

      // Auto-reconnect only when still authenticated and mounted
      if (token) {
        console.log(`[WS] Reconnecting in ${RECONNECT_INTERVAL / 1000}s...`);
        reconnectTimerRef.current = setTimeout(() => {
          reconnectRef.current();
        }, RECONNECT_INTERVAL);
      }
    };

    socket.onerror = (error) => {
      if (intentionalCloseRef.current.has(socket) || !mountedRef.current) {
        return;
      }
      console.error("[WS] Error:", error);
      // onclose will fire after onerror, triggering reconnect
    };
  }, [closeSocket, setShipments, setActivePayload, setNotifications, token]);

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
        reconnectTimerRef.current = null;
      }
      if (socketRef.current) {
        closeSocket(socketRef.current, true);
        socketRef.current = null;
      }
    };
  }, [closeSocket, connect, token]);

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
                <div className={`bg-black/80 border px-3 py-1 flex items-center gap-2 ${isAdmin ? "border-emerald-900/40" : isSeller ? "border-cyan-900/40" : "border-purple-900/40"}`}>
                    {isAdmin
                      ? <ShieldCheck className="w-3 h-3 text-emerald-400" />
                      : isSeller
                        ? <Package className="w-3 h-3 text-cyan-500" />
                        : <ShoppingCart className="w-3 h-3 text-purple-400" />
                    }
                    <div className="flex flex-col">
                      <div className="text-[8px] text-zinc-500 uppercase font-bold">
                        {isAdmin ? "Admin" : isSeller ? "Seller" : "Receiver"}
                      </div>
                      <div className={`text-[10px] font-bold uppercase ${isAdmin ? "text-emerald-400" : isSeller ? "text-cyan-400" : "text-purple-400"}`}>
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
