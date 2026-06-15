"use client";

import {
  CheckCircle2,
  Clock3,
  FileSpreadsheet,
  Flag,
  Gauge,
  ListChecks,
  Radar,
  ShieldCheck,
  X,
  TriangleAlert,
} from "lucide-react";
import { useProposalStore } from "@/lib/store";
import { PHASE_LABELS, SECTION_ORDER, TOTAL_INTERVIEW_QUESTIONS } from "@/lib/types";
import { deriveInterviewAnsweredCount } from "@/lib/workflow-sync";

type StatusTone = "done" | "running" | "waiting" | "attention";

function toneStyle(tone: StatusTone): string {
  switch (tone) {
    case "done":
      return "bg-emerald-100 text-emerald-700";
    case "running":
      return "bg-cyan-100 text-cyan-700";
    case "attention":
      return "bg-amber-100 text-amber-700";
    default:
      return "bg-slate-100 text-slate-600";
  }
}

function toneLabel(tone: StatusTone): string {
  switch (tone) {
    case "done":
      return "Done";
    case "running":
      return "Running";
    case "attention":
      return "Needs action";
    default:
      return "Waiting";
  }
}

export default function OperationsDashboardPanel() {
  const phase = useProposalStore((s) => s.session.currentPhase);
  const interview = useProposalStore((s) => s.interview);
  const sections = useProposalStore((s) => s.proposalSections);
  const validation = useProposalStore((s) => s.validation);
  const requirementsFetched = useProposalStore((s) => s.requirements.fetched);
  const setContextTab = useProposalStore((s) => s.setContextTab);
  const toggleContextPanel = useProposalStore((s) => s.toggleContextPanel);

  const completedPhases = phase - 1;
  const phasePercent = Math.round((completedPhases / 6) * 100);

  const totalInterview = TOTAL_INTERVIEW_QUESTIONS;
  const answeredInterview = deriveInterviewAnsweredCount(interview);
  const interviewPercent = totalInterview > 0 ? Math.round((answeredInterview / totalInterview) * 100) : 0;

  const draftedCount = SECTION_ORDER.filter((sectionKey) => sections[sectionKey].draft !== null).length;
  const approvedCount = SECTION_ORDER.filter((sectionKey) => sections[sectionKey].approved).length;

  const processRows = [
    {
      id: "req",
      label: "ISF requirement extraction",
      detail: requirementsFetched ? "Rules loaded" : "Waiting for requirement pull",
      tone: (requirementsFetched ? "done" : phase >= 2 ? "running" : "waiting") as StatusTone,
    },
    {
      id: "interview",
      label: "Interview intake",
      detail: `${answeredInterview}/${totalInterview} questions answered`,
      tone: (interviewPercent === 100 ? "done" : phase >= 4 ? "running" : "waiting") as StatusTone,
    },
    {
      id: "draft",
      label: "Draft assembly",
      detail: `${draftedCount}/${SECTION_ORDER.length} sections drafted`,
      tone: (draftedCount === SECTION_ORDER.length ? "done" : phase >= 5 ? "running" : "waiting") as StatusTone,
    },
    {
      id: "validation",
      label: "Compliance validation",
      detail: validation.lastRun
        ? `${validation.failed.length} blockers, ${validation.warnings.length} warnings`
        : "Not yet executed",
      tone: (
        validation.lastRun
          ? validation.failed.length > 0
            ? "attention"
            : "done"
          : phase === 6
          ? "running"
          : "waiting"
      ) as StatusTone,
    },
  ];

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-slate-200 px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="font-display text-sm text-slate-900">Operations Dashboard</h3>
            <p className="mt-1 text-xs text-slate-500">Clear view of where the process stands right now.</p>
          </div>
          <button
            onClick={toggleContextPanel}
            className="inline-flex items-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-600 transition-colors hover:bg-slate-50 hover:text-slate-800"
            aria-label="Collapse operations dashboard"
          >
            <X size={12} />
            Close
          </button>
        </div>
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto p-4">
        <section className="rounded-xl border border-slate-200 bg-white p-3">
          <div className="mb-2 flex items-center justify-between gap-2 text-xs">
            <span className="inline-flex items-center gap-1.5 rounded-full bg-teal-50 px-2 py-1 font-semibold text-teal-700">
              <Radar size={12} />
              Phase {phase}: {PHASE_LABELS[phase]}
            </span>
            <span className="text-slate-500">{phasePercent}% complete</span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-gradient-to-r from-teal-500 to-cyan-500" style={{ width: `${Math.max(phasePercent, 6)}%` }} />
          </div>
        </section>

        <section className="grid grid-cols-2 gap-2 text-xs">
          <div className="rounded-xl border border-slate-200 bg-white p-2.5">
            <p className="mb-1 flex items-center gap-1.5 text-slate-500">
              <ListChecks size={12} />
              Interview
            </p>
            <p className="text-sm font-semibold text-slate-900">{answeredInterview}/{totalInterview}</p>
          </div>
          <div className="rounded-xl border border-slate-200 bg-white p-2.5">
            <p className="mb-1 flex items-center gap-1.5 text-slate-500">
              <FileSpreadsheet size={12} />
              Approved sections
            </p>
            <p className="text-sm font-semibold text-slate-900">{approvedCount}/{SECTION_ORDER.length}</p>
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-3">
          <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-700">
            <Gauge size={12} />
            Ongoing processes
          </div>
          <div className="space-y-2">
            {processRows.map((row) => (
              <div key={row.id} className="rounded-lg bg-slate-50 p-2.5">
                <div className="mb-1 flex items-center justify-between gap-2">
                  <p className="text-xs font-semibold text-slate-800">{row.label}</p>
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${toneStyle(row.tone)}`}>
                    {toneLabel(row.tone)}
                  </span>
                </div>
                <p className="text-xs text-slate-500">{row.detail}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-xl border border-slate-200 bg-white p-3">
          <div className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-700">
            <Flag size={12} />
            Submission readiness
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex items-start justify-between gap-2 rounded-lg bg-slate-50 p-2.5">
              <div>
                <p className="font-semibold text-slate-800">Draft package</p>
                <p className="text-slate-500">All proposal sections assembled and approved</p>
              </div>
              <span className={`rounded-full px-2 py-0.5 font-semibold ${toneStyle(approvedCount === SECTION_ORDER.length ? "done" : "running")}`}>
                {approvedCount === SECTION_ORDER.length ? "Ready" : "In progress"}
              </span>
            </div>

            <div className="flex items-start justify-between gap-2 rounded-lg bg-slate-50 p-2.5">
              <div>
                <p className="font-semibold text-slate-800">Compliance report</p>
                <p className="text-slate-500">Validation must pass before submission</p>
              </div>
              <span
                className={`rounded-full px-2 py-0.5 font-semibold ${toneStyle(
                  validation.lastRun
                    ? validation.failed.length > 0
                      ? "attention"
                      : "done"
                    : "waiting"
                )}`}
              >
                {validation.lastRun
                  ? validation.failed.length > 0
                    ? "Blocked"
                    : "Ready"
                  : "Pending"}
              </span>
            </div>

            <div className="flex items-start justify-between gap-2 rounded-lg bg-slate-50 p-2.5">
              <div>
                <p className="font-semibold text-slate-800">Final assembly</p>
                <p className="text-slate-500">Compile final PDF and checklist</p>
              </div>
              <span className={`rounded-full px-2 py-0.5 font-semibold ${toneStyle(validation.readyForSubmission ? "done" : phase === 7 ? "running" : "waiting")}`}>
                {validation.readyForSubmission ? "Ready" : phase === 7 ? "Running" : "Waiting"}
              </span>
            </div>
          </div>
        </section>
      </div>

      <div className="grid grid-cols-3 gap-2 border-t border-slate-200 px-4 py-3">
        <button
          onClick={() => setContextTab("draft")}
          className="inline-flex items-center justify-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          <CheckCircle2 size={12} />
          Drafts
        </button>
        <button
          onClick={() => setContextTab("compliance")}
          className="inline-flex items-center justify-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          {validation.failed.length > 0 ? <TriangleAlert size={12} /> : <Clock3 size={12} />}
          Compliance
        </button>
        <button
          onClick={() => setContextTab("readiness")}
          className="inline-flex items-center justify-center gap-1 rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
        >
          <ShieldCheck size={12} />
          Readiness
        </button>
      </div>
    </div>
  );
}
