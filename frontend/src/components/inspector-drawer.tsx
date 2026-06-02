import React from "react";
import { X, Database, Terminal, ShieldCheck, HeartHandshake, Activity, Layers } from "lucide-react";
import { PipelineTelemetry } from "../types";
import { cn } from "../services/cn";

interface InspectorDrawerProps {
  telemetry?: PipelineTelemetry;
  isOpen: boolean;
  onClose: () => void;
}

export const InspectorDrawer: React.FC<InspectorDrawerProps> = ({ telemetry, isOpen, onClose }) => {
  if (!isOpen) return null;

  const chunks = telemetry?.chunks || [];
  const escalated = telemetry?.escalation_status === "escalated";

  const sourceCategories = React.useMemo(() => {
    if (!chunks.length) return [];
    return Array.from(new Set(chunks.map((c) => c.category.toLowerCase())));
  }, [chunks]);

  const confidenceColor =
    (telemetry?.confidence_score ?? 0) >= 0.80
      ? "text-emerald-400 border-emerald-900/40 bg-emerald-950/15"
      : (telemetry?.confidence_score ?? 0) >= 0.55
      ? "text-amber-400 border-amber-900/40 bg-amber-950/15"
      : "text-rose-400 border-rose-900/40 bg-rose-950/15";

  const guardrailColor =
    telemetry?.guardrail_status === "passed"
      ? "text-emerald-400 border-emerald-900/40 bg-emerald-950/15"
      : "text-rose-400 border-rose-900/40 bg-rose-950/15";

  return (
    <div
      id="inspector-drawer"
      className="fixed inset-y-0 right-0 w-80 md:w-[360px] z-50 flex flex-col font-mono text-zinc-100 drawer-slide-in"
      style={{
        background: "linear-gradient(180deg, #0c0c0f 0%, #09090b 100%)",
        borderLeft: "1px solid rgba(99,102,241,0.15)",
        boxShadow: "-8px 0 32px rgba(0,0,0,0.5), -1px 0 0 rgba(99,102,241,0.08)",
      }}
    >
      {/* Header */}
      <div
        className="flex-shrink-0 px-4 py-3.5 flex justify-between items-center border-b border-zinc-800/60"
        style={{ background: "rgba(9,9,11,0.7)", backdropFilter: "blur(8px)" }}
      >
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-indigo-950/40 border border-indigo-900/40 flex items-center justify-center">
            <Terminal className="h-3.5 w-3.5 text-indigo-400" />
          </div>
          <div>
            <h2 className="text-xs font-bold uppercase tracking-widest text-zinc-200">Pipeline Inspector</h2>
            <p className="text-[9px] text-zinc-600 tracking-wider">Developer Mode Active</p>
          </div>
        </div>
        <button
          id="inspector-close-btn"
          onClick={onClose}
          className="p-1.5 text-zinc-500 hover:text-white hover:bg-zinc-800 rounded-lg transition-all"
          aria-label="Close inspector"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {!telemetry ? (
          <div className="flex flex-col items-center justify-center py-16 text-center text-zinc-600 space-y-3">
            <div className="h-12 w-12 rounded-xl bg-zinc-900 border border-zinc-800 flex items-center justify-center">
              <Terminal className="h-5 w-5 text-zinc-700 animate-pulse" />
            </div>
            <p className="text-[11px] text-zinc-600 max-w-[200px] leading-relaxed">
              Send a message to capture RAG pipeline telemetry here.
            </p>
          </div>
        ) : (
          <>
            {/* ── Section 1: Core Diagnostics ── */}
            <div>
              <div className="flex items-center gap-1.5 mb-2.5">
                <Activity className="h-3.5 w-3.5 text-indigo-400" />
                <span className="text-[9px] font-bold uppercase tracking-widest text-zinc-500">
                  Pipeline Diagnostics
                </span>
              </div>

              <div className="rounded-xl border border-zinc-800/60 overflow-hidden divide-y divide-zinc-800/40"
                style={{ background: "rgba(15,15,18,0.8)" }}>
                {[
                  {
                    label: "Intent",
                    value: telemetry.intent,
                    style: "text-zinc-200 bg-zinc-800/60 border border-zinc-700/40",
                  },
                  {
                    label: "Language",
                    value: telemetry.language,
                    style: "text-zinc-200 bg-zinc-800/60 border border-zinc-700/40 capitalize",
                  },
                  {
                    label: "Route",
                    value: telemetry.route.toUpperCase(),
                    style: "text-zinc-200 bg-zinc-800/60 border border-zinc-700/40",
                  },
                  {
                    label: "Sources",
                    value: sourceCategories.length > 0 ? sourceCategories.join(", ") : "none",
                    style: "text-zinc-300",
                  },
                ].map((row) => (
                  <div key={row.label} className="flex justify-between items-center px-3 py-2.5">
                    <span className="text-[10px] text-zinc-500">{row.label}:</span>
                    <span className={cn("text-[10px] font-semibold px-2 py-0.5 rounded", row.style)}>
                      {row.value}
                    </span>
                  </div>
                ))}

                {/* Confidence Score with bar */}
                <div className="flex justify-between items-center px-3 py-2.5">
                  <span className="text-[10px] text-zinc-500">Confidence:</span>
                  <div className="flex items-center gap-2">
                    <div className="w-20 h-1.5 bg-zinc-800 rounded-full overflow-hidden">
                      <div
                        className={cn("h-full rounded-full transition-all duration-500",
                          (telemetry.confidence_score ?? 0) >= 0.80 ? "bg-emerald-500" :
                          (telemetry.confidence_score ?? 0) >= 0.55 ? "bg-amber-500" : "bg-rose-500"
                        )}
                        style={{ width: `${(telemetry.confidence_score * 100).toFixed(0)}%` }}
                      />
                    </div>
                    <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded border", confidenceColor)}>
                      {(telemetry.confidence_score * 100).toFixed(0)}%
                    </span>
                  </div>
                </div>

                {/* Guardrail Status */}
                <div className="flex justify-between items-center px-3 py-2.5">
                  <span className="text-[10px] text-zinc-500 flex items-center gap-1">
                    <ShieldCheck className="h-3 w-3" /> Guardrail:
                  </span>
                  <span className={cn("text-[10px] font-bold px-2 py-0.5 rounded border", guardrailColor)}>
                    {telemetry.guardrail_status.toUpperCase()}
                  </span>
                </div>
              </div>
            </div>

            {/* ── Section 2: Escalation Detail ── */}
            {escalated && (
              <div
                className="p-3.5 rounded-xl border space-y-2"
                style={{
                  background: "rgba(244,63,94,0.04)",
                  borderColor: "rgba(244,63,94,0.2)",
                }}
              >
                <div className="flex items-center gap-1.5 text-rose-400 font-bold text-[10px] uppercase tracking-wider">
                  <HeartHandshake className="h-3.5 w-3.5" />
                  Escalation Triggered
                </div>
                <div className="space-y-1 text-[10px]">
                  <div className="flex justify-between">
                    <span className="text-zinc-500">Decision:</span>
                    <span className="text-rose-400 font-bold">ESCALATED</span>
                  </div>
                  <div className="flex justify-between gap-4">
                    <span className="text-zinc-500 flex-shrink-0">Trigger:</span>
                    <span className="text-zinc-400 text-right leading-relaxed">
                      {telemetry.escalation_reason || "Low Confidence Fallback"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* ── Section 3: Retrieved FAISS Chunks ── */}
            <div>
              <div className="flex items-center gap-1.5 mb-2.5">
                <Database className="h-3.5 w-3.5 text-indigo-400" />
                <span className="text-[9px] font-bold uppercase tracking-widest text-zinc-500">
                  Retrieved Chunks ({chunks.length})
                </span>
              </div>

              <div className="space-y-2.5">
                {chunks.length === 0 ? (
                  <div
                    className="p-4 rounded-xl text-center text-zinc-600 text-[10px] border border-zinc-800/40"
                    style={{ background: "rgba(15,15,18,0.6)" }}
                  >
                    No vectors retrieved — direct bypass route.
                  </div>
                ) : (
                  chunks.map((chunk, idx) => {
                    const pct = (chunk.score * 100).toFixed(0);
                    const isHighScore = chunk.score >= 0.85;
                    return (
                      <div
                        key={idx}
                        className="rounded-xl border border-zinc-800/50 overflow-hidden transition-all hover:border-zinc-700/60"
                        style={{ background: "rgba(15,15,18,0.7)" }}
                      >
                        {/* Chunk Header */}
                        <div className="flex justify-between items-center px-3 py-2 border-b border-zinc-800/40">
                          <div className="flex items-center gap-1.5">
                            <Layers className="h-3 w-3 text-indigo-500" />
                            <span className="text-[9px] font-bold text-indigo-400 uppercase tracking-wider">
                              {chunk.category}
                            </span>
                            <span className="text-zinc-700">/</span>
                            <span className="text-[9px] text-zinc-500 uppercase">{chunk.subsection}</span>
                          </div>
                          <span
                            className={cn(
                              "text-[9px] font-bold px-2 py-0.5 rounded border",
                              isHighScore
                                ? "text-emerald-400 border-emerald-900/40 bg-emerald-950/15"
                                : "text-amber-400 border-amber-900/40 bg-amber-950/15"
                            )}
                          >
                            {pct}%
                          </span>
                        </div>
                        {/* Chunk Score Bar */}
                        <div className="h-0.5 bg-zinc-800">
                          <div
                            className={cn("h-full transition-all", isHighScore ? "bg-emerald-500/60" : "bg-amber-500/60")}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                        {/* Chunk Content */}
                        <p className="px-3 py-2.5 text-[10px] text-zinc-400 leading-relaxed">
                          {chunk.content}
                        </p>
                      </div>
                    );
                  })
                )}
              </div>
            </div>

            {/* Session Info */}
            <div className="pb-2 text-[9px] text-zinc-700 text-center font-mono tracking-wider">
              Session: {telemetry.session_id?.slice(0, 20)}...
            </div>
          </>
        )}
      </div>
    </div>
  );
};
