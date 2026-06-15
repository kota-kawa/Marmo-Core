"use client";

import { AlertTriangle, CheckCircle2, Clock3, Gauge, ShieldCheck } from "lucide-react";
import { useMemo } from "react";
import { useProposalStore } from "@/lib/store";
import { buildReadinessSnapshot, type ReadinessStatus } from "@/lib/readiness";

interface SubmissionReadinessPanelProps {
  onAction?: (action: string) => void;
}

function statusStyles(status: ReadinessStatus): string {
  if (status === "ready") return "bg-emerald-100 text-emerald-700";
  if (status === "in_progress") return "bg-cyan-100 text-cyan-700";
  return "bg-amber-100 text-amber-700";
}

function statusLabel(status: ReadinessStatus): string {
  if (status === "ready") return "Ready";
  if (status === "in_progress") return "In progress";
  return "Blocked";
}

export default function SubmissionReadinessPanel({ onAction }: SubmissionReadinessPanelProps) {
  const researcherInfo = useProposalStore((s) => s.researcherInfo);
  const proposalSections = useProposalStore((s) => s.proposalSections);
  const validation = useProposalStore((s) => s.validation);
  const referenceSources = useProposalStore((s) => s.referenceSources);

  const snapshot = useMemo(
    () =>
      buildReadinessSnapshot({
        researcherInfo,
        proposalSections,
        validation,
        referenceSources,
      }),
    [proposalSections, referenceSources, researcherInfo, validation]
  );

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-slate-200 px-4 py-3">
        <h3 className="font-display text-sm text-slate-900">Submission Readiness</h3>
        <p className="mt-1 text-xs text-slate-500">Track blockers before final assembly.</p>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        <section className="rounded-xl border border-slate-200 bg-white p-3">
          <div className="mb-2 flex items-center justify-between text-xs">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-teal-50 px-2 py-1 font-semibold text-teal-700">
              <Gauge size={12} />
              Readiness score
            </span>
            <span className="font-semibold text-slate-700">{snapshot.score}%</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-200">
            <div
              className="h-full rounded-full bg-gradient-to-r from-teal-500 to-cyan-500"
              style={{ width: `${Math.max(snapshot.score, 6)}%` }}
            />
          </div>
          <div className="mt-2 flex items-center gap-2 text-xs text-slate-500">
            <span className="inline-flex items-center gap-1">
              <AlertTriangle size={12} className="text-amber-500" />
              {snapshot.blockers} blocker(s)
            </span>
            <span className="inline-flex items-center gap-1">
              <Clock3 size={12} className="text-cyan-600" />
              {snapshot.inProgress} in progress
            </span>
            <span className="inline-flex items-center gap-1">
              <CheckCircle2 size={12} className="text-emerald-600" />
              {snapshot.items.length - snapshot.blockers - snapshot.inProgress} ready
            </span>
          </div>
        </section>

        <section className="space-y-2">
          {snapshot.items.map((item) => (
            <div key={item.id} className="rounded-xl border border-slate-200 bg-white p-3">
              <div className="mb-1 flex items-center justify-between gap-2">
                <p className="text-xs font-semibold text-slate-800">{item.title}</p>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusStyles(item.status)}`}>
                  {statusLabel(item.status)}
                </span>
              </div>
              <p className="text-xs leading-relaxed text-slate-500">{item.detail}</p>
              {item.action && item.status !== "ready" && (
                <button
                  onClick={() => {
                    if (!item.action) return;
                    onAction?.(item.action);
                  }}
                  className="mt-2 text-xs font-semibold text-teal-700 hover:text-teal-800"
                >
                  Resolve now
                </button>
              )}
            </div>
          ))}
        </section>
      </div>

      <div className="grid grid-cols-2 gap-2 border-t border-slate-200 px-4 py-3">
        <button
          onClick={() => onAction?.("/validate")}
          className="inline-flex items-center justify-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          <ShieldCheck size={12} />
          Run check
        </button>
        <button
          onClick={() => onAction?.("open-compliance")}
          className="inline-flex items-center justify-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          <AlertTriangle size={12} />
          View blockers
        </button>
      </div>
    </div>
  );
}
