"use client";

import { useMemo, useState, useEffect } from "react";
import { useLogisticsStore } from "@/store/useLogisticsStore";
import { useAuthStore } from "@/store/useAuthStore";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { RadioTower, CloudSun, Anchor, Truck, AlertTriangle, Package, ShoppingCart, LogOut, Zap, Cloud, Ship, FileWarning, Users, Shield } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function DataLayersPanel() {
  const {
    layers,
    shipments,
    notifications,
    systemMessage,
    isInjecting,
    toggleLayer,
    injectDemoSignal,
    scheduleTransport,
    updateTruckGps,
    notifyStakeholders,
  } = useLogisticsStore();

  const { role, fullName, logout } = useAuthStore();
  const isAdmin = role === "admin";
  const isSeller = role === "seller";
  const isReceiver = role === "receiver";
  const canSimulateDisruptions = isAdmin;

  const [disruptionTarget, setDisruptionTarget] = useState("");

  const [origin, setOrigin] = useState(isSeller ? "Chennai" : "Mumbai");
  const [destination, setDestination] = useState(isSeller ? "Bangalore" : "Delhi");
  const [cargo, setCargo] = useState(isSeller ? "Cold-chain Pharma" : "Electronics");
  const [priority, setPriority] = useState<"LOW" | "MEDIUM" | "HIGH" | "CRITICAL">("HIGH");
  const [startInMinutes, setStartInMinutes] = useState(60);
  const [selectedShipmentId, setSelectedShipmentId] = useState("");
  const [scheduleError, setScheduleError] = useState<string | null>(null);
  const [knownCities, setKnownCities] = useState<string[]>([]);

  // Fetch city list for autocomplete
  useEffect(() => {
    fetch(`${API_URL}/api/cities`)
      .then((r) => r.json())
      .then((d) => setKnownCities(d.cities || []))
      .catch(() => {});
  }, []);

  const selectedShipment = useMemo(
    () => shipments.find((s) => s.id === selectedShipmentId),
    [shipments, selectedShipmentId]
  );

  const onSchedule = async () => {
    setScheduleError(null);
    const result = await scheduleTransport({
      origin,
      destination,
      cargo,
      priority,
      start_in_minutes: startInMinutes,
    });
    // scheduleTransport returns the raw data object so we can inspect it
    if (result && (result as {status?: string}).status === "error") {
      setScheduleError((result as {message?: string}).message || "Unknown error");
    }
  };

  const onPushGps = async () => {
    if (!selectedShipment) return;
    const lat = (selectedShipment.currentLat ?? 20.5937) + ((Math.random() - 0.5) * 0.06);
    const lon = (selectedShipment.currentLon ?? 78.9629) + ((Math.random() - 0.5) * 0.06);
    await updateTruckGps(selectedShipment.id, lat, lon);
  };

  return (
    <div className="h-full w-[300px] glass-panel p-4 flex flex-col gap-6 z-10 overflow-y-auto">
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-bold tracking-[0.3em] text-cyan-400 uppercase">System Intelligence</h2>
          <button
            onClick={logout}
            title="Logout"
            className="p-1 text-zinc-600 hover:text-red-400 transition-colors"
          >
            <LogOut className="w-3 h-3" />
          </button>
        </div>
        {/* Role badge */}
        <div className={`flex items-center gap-1.5 px-1 py-0.5 w-fit border ${isAdmin ? "border-emerald-900/40 bg-emerald-950/10" : isSeller ? "border-cyan-900/40 bg-cyan-950/10" : "border-purple-900/40 bg-purple-950/10"}`}>
          {isAdmin
            ? <Shield className="w-2.5 h-2.5 text-emerald-500" />
            : isSeller
              ? <Package className="w-2.5 h-2.5 text-cyan-600" />
              : <ShoppingCart className="w-2.5 h-2.5 text-purple-500" />
          }
          <span className={`text-[8px] uppercase tracking-widest font-bold ${isAdmin ? "text-emerald-500" : isSeller ? "text-cyan-600" : "text-purple-500"}`}>
            {fullName || (isAdmin ? "Admin" : isSeller ? "Seller" : "Receiver")}
          </span>
        </div>
        <div className="h-[1px] w-full bg-cyan-900/40" />
      </div>

      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between space-x-2">
          <div className="flex items-center gap-3">
            <RadioTower className="w-4 h-4 text-cyan-500" />
            <Label htmlFor="news" className="text-xs uppercase tracking-wider text-zinc-400 cursor-pointer">Live News Feed</Label>
          </div>
          <Switch 
            id="news" 
            checked={layers.news} 
            onCheckedChange={() => toggleLayer("news")}
            className="data-[state=checked]:bg-cyan-500"
          />
        </div>

        <div className="flex items-center justify-between space-x-2">
          <div className="flex items-center gap-3">
            <CloudSun className="w-4 h-4 text-cyan-500" />
            <Label htmlFor="weather" className="text-xs uppercase tracking-wider text-zinc-400 cursor-pointer">Weather Radar</Label>
          </div>
          <Switch 
            id="weather" 
            checked={layers.weather} 
            onCheckedChange={() => toggleLayer("weather")}
            className="data-[state=checked]:bg-cyan-500"
          />
        </div>

        <div className="flex items-center justify-between space-x-2">
          <div className="flex items-center gap-3">
            <Anchor className="w-4 h-4 text-cyan-500" />
            <Label htmlFor="ports" className="text-xs uppercase tracking-wider text-zinc-400 cursor-pointer">Port Congestion</Label>
          </div>
          <Switch 
            id="ports" 
            checked={layers.ports} 
            onCheckedChange={() => toggleLayer("ports")}
            className="data-[state=checked]:bg-cyan-500"
          />
        </div>

        <div className="flex items-center justify-between space-x-2">
          <div className="flex items-center gap-3">
            <Truck className="w-4 h-4 text-cyan-500" />
            <Label htmlFor="shipments" className="text-xs uppercase tracking-wider text-zinc-400 cursor-pointer">Active Shipments</Label>
          </div>
          <Switch 
            id="shipments" 
            checked={layers.shipments} 
            onCheckedChange={() => toggleLayer("shipments")}
            className="data-[state=checked]:bg-cyan-500"
          />
        </div>
      </div>

      <div className="mt-auto pt-6 flex flex-col gap-4">
        <div className={`p-3 border flex flex-col gap-2 ${isAdmin ? "border-emerald-900/30 bg-emerald-950/10" : isSeller ? "border-cyan-900/30 bg-cyan-950/10" : "border-purple-900/30 bg-purple-950/10"}`}>
          <div className="flex items-center gap-2">
            {isAdmin
              ? <Shield className="w-3 h-3 text-emerald-400" />
              : isSeller
                ? <Package className="w-3 h-3 text-cyan-500" />
                : <ShoppingCart className="w-3 h-3 text-purple-400" />
            }
            <span className={`text-[10px] uppercase tracking-widest font-bold ${isAdmin ? "text-emerald-400" : isSeller ? "text-cyan-500" : "text-purple-400"}`}>
              {isAdmin ? "Control Tower" : isSeller ? "Send Product" : "Receive Product"}
            </span>
          </div>
          <div className="text-[8px] uppercase tracking-wider mb-1 text-zinc-600">
            {isAdmin
              ? "Create or supervise shipments"
              : isSeller
                ? "Schedule outbound shipment"
                : "Read-only receiver tracking"}
          </div>
          {/* City autocomplete datalist */}
          <datalist id="city-list">
            {knownCities.map((city) => <option key={city} value={city} />)}
          </datalist>
          <input
            value={origin}
            onChange={(e) => { setOrigin(e.target.value); setScheduleError(null); }}
            placeholder={isSeller ? "Dispatch from (origin)" : "Ship from (seller location)"}
            list="city-list"
            className={`w-full px-2 py-1 bg-black/40 border text-[10px] text-zinc-200 ${isSeller ? "border-cyan-900/30" : "border-purple-900/30"}`}
          />
          <input
            value={destination}
            onChange={(e) => { setDestination(e.target.value); setScheduleError(null); }}
            placeholder={isSeller ? "Deliver to (destination)" : "Deliver to (my location)"}
            list="city-list"
            className={`w-full px-2 py-1 bg-black/40 border text-[10px] text-zinc-200 ${isSeller ? "border-cyan-900/30" : "border-purple-900/30"}`}
          />
          <input
            value={cargo}
            onChange={(e) => setCargo(e.target.value)}
            placeholder="Cargo description"
            className={`w-full px-2 py-1 bg-black/40 border text-[10px] text-zinc-200 ${isSeller ? "border-cyan-900/30" : "border-purple-900/30"}`}
          />
          <div className="grid grid-cols-2 gap-2">
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value as "LOW" | "MEDIUM" | "HIGH" | "CRITICAL")}
              className={`px-2 py-1 bg-black/40 border text-[10px] text-zinc-200 ${isSeller ? "border-cyan-900/30" : "border-purple-900/30"}`}
            >
              <option value="LOW">LOW</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="HIGH">HIGH</option>
              <option value="CRITICAL">CRITICAL</option>
            </select>
            <input
              type="number"
              value={startInMinutes}
              onChange={(e) => setStartInMinutes(Number(e.target.value))}
              className={`px-2 py-1 bg-black/40 border text-[10px] text-zinc-200 ${isSeller ? "border-cyan-900/30" : "border-purple-900/30"}`}
              min={0}
            />
          </div>
          {scheduleError && (
            <div className="px-2 py-1.5 border border-red-900/50 bg-red-950/10 text-[9px] text-red-400 uppercase leading-relaxed">
              ⚠ {scheduleError}
            </div>
          )}
          <button
            onClick={onSchedule}
            disabled={isReceiver}
            className={`mt-1 w-full py-2 border text-[10px] uppercase tracking-widest font-bold transition-colors ${
              isAdmin
                ? "bg-emerald-600/20 border-emerald-600/50 text-emerald-300 hover:bg-emerald-600/40"
                : isSeller
                ? "bg-cyan-600/20 border-cyan-600/50 text-cyan-400 hover:bg-cyan-600/40"
                : "bg-purple-600/20 border-purple-600/50 text-purple-300 hover:bg-purple-600/40"
            } disabled:opacity-40`}
          >
            {isReceiver ? "Receiver Read-only" : isSeller ? "Dispatch Shipment →" : "Create / Supervise"}
          </button>
        </div>

        <div className="p-3 border border-indigo-900/30 bg-indigo-950/10 flex flex-col gap-2">
          <span className="text-[10px] text-indigo-400 uppercase tracking-widest font-bold">Truck GPS + Alerts</span>
          <select
            value={selectedShipmentId}
            onChange={(e) => setSelectedShipmentId(e.target.value)}
            className="w-full px-2 py-1 bg-black/40 border border-indigo-900/30 text-[10px] text-zinc-200"
          >
            <option value="">Select shipment</option>
            {shipments.map((s) => (
              <option key={s.id} value={s.id}>{s.id}</option>
            ))}
          </select>
          <button
            onClick={onPushGps}
            disabled={!selectedShipment || isReceiver}
            className="w-full py-2 bg-indigo-600/20 border border-indigo-600/50 text-indigo-300 text-[10px] uppercase tracking-widest font-bold hover:bg-indigo-600/40 transition-colors disabled:opacity-40"
          >
            Push Truck GPS
          </button>
          <button
            onClick={() => selectedShipment && notifyStakeholders(selectedShipment.id)}
            disabled={!selectedShipment || isReceiver}
            className="w-full py-2 bg-emerald-600/20 border border-emerald-600/50 text-emerald-300 text-[10px] uppercase tracking-widest font-bold hover:bg-emerald-600/40 transition-colors disabled:opacity-40"
          >
            Notify Seller + Receiver
          </button>
          {selectedShipment && (
            <div className="text-[9px] text-zinc-500 uppercase leading-relaxed">
              {selectedShipment.id} | risk {selectedShipment.riskScore}%
            </div>
          )}
        </div>

        <div className="p-3 border border-amber-900/30 bg-amber-950/10 flex flex-col gap-2">
            <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full bg-amber-500 ${isInjecting ? "animate-ping" : "animate-pulse"}`} />
                <span className="text-[10px] text-amber-500 uppercase tracking-widest font-bold">Disruption Signals</span>
            </div>
            <p className="text-[9px] text-zinc-500 uppercase leading-tight mb-1">
                Inject a simulated disruption to test the AI agent pipeline end-to-end.
            </p>

            {/* Target route selector — admin picks which shipment to disrupt */}
            {canSimulateDisruptions && (
              <div className="flex flex-col gap-1">
                <span className="text-[8px] text-zinc-600 uppercase tracking-widest">Target Route</span>
                <select
                  value={disruptionTarget}
                  onChange={(e) => setDisruptionTarget(e.target.value)}
                  disabled={isInjecting}
                  className="w-full px-2 py-1 bg-black/40 border border-amber-900/40 text-[10px] text-zinc-200 disabled:opacity-40"
                >
                  <option value="">All routes (AI auto-selects)</option>
                  {shipments.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.id}{s.riskScore > 0 ? ` — risk ${s.riskScore}%` : ""}
                    </option>
                  ))}
                </select>
                {disruptionTarget && (
                  <div className="text-[8px] text-amber-400 uppercase tracking-widest animate-pulse">
                    ⚡ Disruption anchored on {disruptionTarget}
                  </div>
                )}
              </div>
            )}

            {/* Signal type buttons — only admin can inject simulation */}
            <div className="grid grid-cols-2 gap-1.5">
              {/* Weather / Cyclone */}
              <button
                onClick={() => injectDemoSignal("weather", disruptionTarget || undefined)}
                disabled={isInjecting || !canSimulateDisruptions}
                title="Cyclone warning — Gujarat coast, port shutdown"
                className="flex items-center gap-1.5 px-2 py-1.5 bg-sky-900/20 border border-sky-700/40 text-sky-300 text-[9px] uppercase tracking-widest font-bold hover:bg-sky-700/30 transition-colors disabled:opacity-40"
              >
                <Cloud className="w-3 h-3 shrink-0" />
                Weather
              </button>

              {/* Port Congestion */}
              <button
                onClick={() => injectDemoSignal("port_congestion", disruptionTarget || undefined)}
                disabled={isInjecting || !canSimulateDisruptions}
                title="JNPT Mumbai strike — 4-day backlog"
                className="flex items-center gap-1.5 px-2 py-1.5 bg-teal-900/20 border border-teal-700/40 text-teal-300 text-[9px] uppercase tracking-widest font-bold hover:bg-teal-700/30 transition-colors disabled:opacity-40"
              >
                <Ship className="w-3 h-3 shrink-0" />
                Port
              </button>

              {/* Road Closure */}
              <button
                onClick={() => injectDemoSignal("road_closure", disruptionTarget || undefined)}
                disabled={isInjecting || !canSimulateDisruptions}
                title="NH-44 pile-up near Nagpur — 6hr delay"
                className="flex items-center gap-1.5 px-2 py-1.5 bg-orange-900/20 border border-orange-700/40 text-orange-300 text-[9px] uppercase tracking-widest font-bold hover:bg-orange-700/30 transition-colors disabled:opacity-40"
              >
                <Truck className="w-3 h-3 shrink-0" />
                Road
              </button>

              {/* Customs Delay */}
              <button
                onClick={() => injectDemoSignal("customs_delay", disruptionTarget || undefined)}
                disabled={isInjecting || !canSimulateDisruptions}
                title="Delhi ICD enhanced inspection — 72hr clearance"
                className="flex items-center gap-1.5 px-2 py-1.5 bg-yellow-900/20 border border-yellow-700/40 text-yellow-300 text-[9px] uppercase tracking-widest font-bold hover:bg-yellow-700/30 transition-colors disabled:opacity-40"
              >
                <FileWarning className="w-3 h-3 shrink-0" />
                Customs
              </button>

              {/* Civil Unrest */}
              <button
                onClick={() => injectDemoSignal("civil_unrest", disruptionTarget || undefined)}
                disabled={isInjecting || !canSimulateDisruptions}
                title="Kolkata protests — NH-12 and freight rail closed"
                className="flex items-center gap-1.5 px-2 py-1.5 bg-red-900/20 border border-red-700/40 text-red-300 text-[9px] uppercase tracking-widest font-bold hover:bg-red-700/30 transition-colors disabled:opacity-40"
              >
                <Users className="w-3 h-3 shrink-0" />
                Unrest
              </button>

              {/* Auto (real APIs) */}
              <button
                onClick={() => injectDemoSignal("auto", disruptionTarget || undefined)}
                disabled={isInjecting || !canSimulateDisruptions}
                title="Fetch live signals from real APIs then run AI pipeline"
                className="flex items-center gap-1.5 px-2 py-1.5 bg-amber-900/20 border border-amber-700/40 text-amber-300 text-[9px] uppercase tracking-widest font-bold hover:bg-amber-700/30 transition-colors disabled:opacity-40"
              >
                <Zap className="w-3 h-3 shrink-0" />
                Auto
              </button>
            </div>

            {isInjecting && (
              <div className="text-[8px] text-amber-400 uppercase tracking-widest animate-pulse">
                ▶ Pipeline running — awaiting agent response…
              </div>
            )}
            {!canSimulateDisruptions && (
              <div className="text-[8px] text-zinc-500 uppercase tracking-widest">
                Only admin can simulate disruption scenarios.
              </div>
            )}
        </div>

        <div className="p-3 border border-emerald-900/30 bg-emerald-950/10 flex flex-col gap-2">
          <span className="text-[10px] text-emerald-400 uppercase tracking-widest font-bold">Recent Notifications</span>
          {notifications.length === 0 ? (
            <div className="text-[9px] text-zinc-600 uppercase">Awaiting notifications</div>
          ) : (
            notifications.slice(-3).reverse().map((notification) => (
              <div key={notification.id} className="border border-emerald-900/20 bg-black/20 px-2 py-1">
                <div className="text-[8px] text-emerald-400 uppercase tracking-widest">{notification.channel}</div>
                <div className="text-[9px] text-zinc-400 leading-relaxed">{notification.message}</div>
              </div>
            ))
          )}
        </div>
        
        <div className="flex items-center gap-2 text-[10px] text-zinc-600 uppercase tracking-widest font-mono italic">
            <AlertTriangle className="w-3 h-3" />
            System: {systemMessage || "Nominal"}
        </div>
      </div>
    </div>
  );
}
