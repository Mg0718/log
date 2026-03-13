"use client";

import { useEffect, useState } from "react";
import { useLogisticsStore } from "@/store/useLogisticsStore";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal, ShieldAlert, Cpu, Route, CheckCircle2, XCircle } from "lucide-react";

export function AgentHUD() {
  const { activePayload, notifications, sendAgentDecision } = useLogisticsStore();
  const [displayText, setDisplayText] = useState("");
  const fullText = !activePayload
    ? ""
    : activePayload.agent === "RiskAnalyst"
      ? (activePayload.affected_shipments[0]?.reasoning_log || "")
      : activePayload.agent === "ActionComposer"
        ? `${activePayload.proposed_action.header}\nRECOMMENDED: ${activePayload.proposed_action.recommended_option || "REVIEW"}\n${activePayload.proposed_action.driver_sms_draft}`
        : `OPTIMIZING ROUTE FOR ${activePayload.shipment_id}...`;

  useEffect(() => {
    if (fullText === displayText) {
      return;
    }

    const timeout = setTimeout(() => {
      if (!fullText) {
        setDisplayText("");
        return;
      }

      if (!fullText.startsWith(displayText)) {
        setDisplayText(fullText.slice(0, 1));
        return;
      }

      setDisplayText(fullText.slice(0, displayText.length + 1));
    }, 20);

    return () => clearTimeout(timeout);
  }, [displayText, fullText]);

  return (
    <div className="h-full w-[400px] glass-panel p-4 flex flex-col gap-4 z-10 font-mono">
      <div className="flex flex-col gap-1">
        <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold tracking-[0.3em] text-cyan-400 uppercase flex items-center gap-2">
                <Terminal className="w-3 h-3" />
                Agent Telemetry
            </h2>
            {activePayload && (
                <div className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-cyan-500 animate-pulse" />
                    <span className="text-[10px] text-cyan-500 font-bold uppercase tracking-tighter">Active</span>
                </div>
            )}
        </div>
        <div className="h-[1px] w-full bg-cyan-900/40" />
      </div>

      <div className="flex-1 overflow-y-auto flex flex-col gap-4 py-2 custom-scrollbar">
        <AnimatePresence mode="wait">
          {!activePayload ? (
            <motion.div 
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center h-full gap-4 text-zinc-700"
            >
              <Cpu className="w-8 h-8 opacity-20" />
              <p className="text-[10px] uppercase tracking-[0.2em] text-center">Awaiting data stream...</p>
            </motion.div>
          ) : (
            <motion.div 
              key={activePayload.agent}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              className="flex flex-col gap-4"
            >
              {/* Agent Badge */}
              <div className="flex items-center gap-3 p-2 bg-cyan-500/5 border border-cyan-500/20">
                <div className="w-8 h-8 flex items-center justify-center bg-cyan-500/10 border border-cyan-500/30">
                    {activePayload.agent === "RiskAnalyst" && <ShieldAlert className="w-4 h-4 text-red-500" />}
                    {activePayload.agent === "RouteOptimizer" && <Route className="w-4 h-4 text-amber-500" />}
                    {activePayload.agent === "ActionComposer" && <CheckCircle2 className="w-4 h-4 text-green-500" />}
                </div>
                <div>
                    <div className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold">Process Origin</div>
                    <div className="text-xs text-cyan-400 uppercase tracking-wider font-bold">{activePayload.agent}</div>
                </div>
              </div>

              {/* Reasoning Log / Terminal */}
              <div className="flex flex-col gap-2 p-3 bg-black/40 border border-cyan-900/20 min-h-[120px]">
                <div className="text-[9px] text-zinc-500 uppercase flex items-center justify-between">
                    <span>LOG_OUTPUT v1.0.4</span>
                    <span className="animate-pulse">_</span>
                </div>
                <div className="text-xs text-zinc-300 leading-relaxed break-words">
                  {displayText}
                  <span className="inline-block w-1.5 h-3 bg-cyan-500 ml-1 animate-pulse" />
                </div>
              </div>

              {/* Action Buttons if ActionComposer */}
              {activePayload.agent === "ActionComposer" && (
                <div className="flex flex-col gap-3 mt-4">
                  {(activePayload.proposed_action.decision_options ?? []).map((option, index) => (
                    <button
                      key={option.id}
                      onClick={() => sendAgentDecision(activePayload.shipment_id, option.decision as "APPROVE" | "REJECT")}
                      className={index === 0
                        ? "w-full py-4 bg-cyan-500 text-black font-bold uppercase tracking-[0.2em] text-sm hover:bg-cyan-400 transition-all flex items-center justify-center gap-3"
                        : "w-full py-4 bg-transparent border border-red-900/40 text-red-500 font-bold uppercase tracking-[0.2em] text-sm hover:bg-red-500/10 transition-all flex items-center justify-center gap-3"
                      }
                    >
                      {index === 0 ? <CheckCircle2 className="w-5 h-5" /> : <XCircle className="w-5 h-5" />}
                      {option.label}
                    </button>
                  ))}
                </div>
              )}
              
              {/* Data Table if RiskAnalyst */}
              {activePayload.agent === "RiskAnalyst" && (
                  <div className="flex flex-col gap-2">
                      <div className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold px-1">Affected Units</div>
                      {activePayload.affected_shipments.map((shipment) => (
                          <div key={shipment.shipment_id} className="p-3 bg-red-950/10 border border-red-900/30 flex items-center justify-between">
                              <div>
                                  <div className="text-xs text-red-400 font-bold">{shipment.shipment_id}</div>
                                  <div className="text-[10px] text-zinc-500 uppercase">Risk Level: {shipment.severity}</div>
                              </div>
                              <div className="text-right">
                                  <div className="text-lg font-bold text-red-500">{shipment.risk_score}%</div>
                                  <div className="text-[8px] text-red-900 font-bold uppercase">Critical</div>
                              </div>
                          </div>
                      ))}
                  </div>
              )}

              {/* Route Alternatives if RouteOptimizer */}
              {activePayload.agent === "RouteOptimizer" && (
                  <div className="flex flex-col gap-2">
                       <div className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold px-1">Proposed Detours</div>
                       {activePayload.calculated_alternatives.map((alt) => (
                          <div key={alt.option_id} className="p-3 bg-amber-950/10 border border-amber-900/30 flex items-center justify-between">
                              <div>
                                  <div className="text-xs text-amber-400 font-bold">{alt.option_id}</div>
                                  <div className="text-[10px] text-zinc-500 uppercase">ETA DELTA: {alt.eta_delta_minutes}m</div>
                              </div>
                              <div className="text-right">
                                  <div className="text-xs font-bold text-amber-500">{alt.cost_delta_inr} INR</div>
                                  <div className="text-[8px] text-amber-900 font-bold uppercase">Optimized</div>
                              </div>
                          </div>
                      ))}
                  </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="border-t border-cyan-900/20 pt-3">
        <div className="text-[10px] text-zinc-500 uppercase tracking-widest font-bold mb-2">Stakeholder Notifications</div>
        <div className="flex flex-col gap-2 max-h-40 overflow-y-auto custom-scrollbar pr-1">
          {notifications.length === 0 ? (
            <div className="text-[10px] text-zinc-700 uppercase">No notifications yet</div>
          ) : (
            notifications.slice(-4).reverse().map((notification) => (
              <div key={notification.id} className="p-2 bg-black/30 border border-cyan-900/20">
                <div className="text-[9px] text-cyan-500 uppercase tracking-widest">{notification.channel}</div>
                <div className="text-[10px] text-zinc-300 leading-relaxed">{notification.message}</div>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="mt-auto pt-4 border-t border-cyan-900/20">
        <div className="flex items-center justify-between text-[8px] text-zinc-600 uppercase tracking-tighter">
            <span>Lat: 12.9716° N</span>
            <span>Lon: 77.5946° E</span>
            <span suppressHydrationWarning>UTC: {new Date().toISOString().slice(11, 19)}</span>
        </div>
      </div>
    </div>
  );
}
