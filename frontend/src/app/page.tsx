"use client";

import dynamic from "next/dynamic";
import { DataLayersPanel } from "@/components/DataLayersPanel";
import { AgentHUD } from "@/components/AgentHUD";

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

export default function Home() {
  return (
    <div className="flex h-screen w-screen overflow-hidden bg-black p-2 gap-2">
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
                <div className="bg-black/80 border border-cyan-900/40 px-3 py-1 flex flex-col items-end">
                    <div className="text-[8px] text-zinc-500 uppercase font-bold">Network Status</div>
                    <div className="text-[10px] text-cyan-400 font-bold uppercase flex items-center gap-2">
                        <div className="w-1 h-1 bg-cyan-400 rounded-full animate-ping" />
                        Encrypted
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
    </div>
  );
}
