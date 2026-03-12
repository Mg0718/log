"use client";

import { useLogisticsStore } from "@/store/useLogisticsStore";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { RadioTower, CloudSun, Anchor, Truck, AlertTriangle } from "lucide-react";

export function DataLayersPanel() {
  const { layers, toggleLayer, injectDemoSignal } = useLogisticsStore();

  return (
    <div className="h-full w-[300px] glass-panel p-4 flex flex-col gap-6 z-10">
      <div className="flex flex-col gap-1">
        <h2 className="text-xs font-bold tracking-[0.3em] text-cyan-400 uppercase">System Intelligence</h2>
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
        <div className="p-3 border border-amber-900/30 bg-amber-950/10 flex flex-col gap-2">
            <div className="flex items-center gap-2">
                <div className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                <span className="text-[10px] text-amber-500 uppercase tracking-widest font-bold">Simulation Mode</span>
            </div>
            <p className="text-[10px] text-zinc-500 leading-tight uppercase">
                Inject a simulated disruption event to test AI agent response and routing logic.
            </p>
            <button 
                onClick={injectDemoSignal}
                className="mt-2 w-full py-2 bg-amber-600/20 border border-amber-600/50 text-amber-500 text-[10px] uppercase tracking-widest font-bold hover:bg-amber-600/40 transition-colors"
            >
                Inject Signal
            </button>
        </div>
        
        <div className="flex items-center gap-2 text-[10px] text-zinc-600 uppercase tracking-widest font-mono italic">
            <AlertTriangle className="w-3 h-3" />
            System: Nominal
        </div>
      </div>
    </div>
  );
}
