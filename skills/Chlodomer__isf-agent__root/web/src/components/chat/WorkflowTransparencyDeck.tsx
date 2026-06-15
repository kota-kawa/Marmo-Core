"use client";

import { useMemo, useState } from "react";
import {
  Activity,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  ClipboardCheck,
  Clock3,
  FileUp,
  Gauge,
  PlayCircle,
  Radar,
  Send,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import { useProposalStore } from "@/lib/store";
import { PHASE_LABELS, SECTION_ORDER, TOTAL_INTERVIEW_QUESTIONS, type ChatMessage } from "@/lib/types";
import { deriveInterviewAnsweredCount } from "@/lib/workflow-sync";

interface WorkflowTransparencyDeckProps {
  onAction: (action: string) => void;
}

type ProcessState = "queued" | "running" | "complete" | "attention";

interface ProcessItem {
  id: string;
  label: string;
  detail: string;
  progress: number;
  state: ProcessState;
}

interface SubmissionItem {
  id: string;
  label: string;
  state: "missing" | "in_progress" | "ready" | "blocked";
  helper: string;
}

function processStyles(state: ProcessState): string {
  switch (state) {
    case "complete":
      return "bg-[#e9dccb] text-[#775336]";
    case "running":
      return "bg-[#e5e9ed] text-[#4f5f6f]";
    case "attention":
      return "bg-[#f2e4d1] text-[#8a603e]";
    default:
      return "bg-[#ede8e1] text-[#64584b]";
  }
}

function processLabel(state: ProcessState): string {
  switch (state) {
    case "complete":
      return "Done";
    case "running":
      return "Running";
    case "attention":
      return "Needs input";
    default:
      return "Queued";
  }
}

function processIcon(state: ProcessState) {
  switch (state) {
    case "complete":
      return CheckCircle2;
    case "running":
      return PlayCircle;
    case "attention":
      return TriangleAlert;
    default:
      return Clock3;
  }
}

function submissionBadge(state: SubmissionItem["state"]): string {
  switch (state) {
    case "ready":
      return "bg-[#e9dccb] text-[#765238]";
    case "in_progress":
      return "bg-[#e5e9ed] text-[#4d5d6b]";
    case "blocked":
      return "bg-[#f2e4d1] text-[#89603f]";
    default:
      return "bg-[#ece8e1] text-[#65594b]";
  }
}

function getLatestAgentUpdate(messages: ChatMessage[]): string {
  const update = [...messages]
    .reverse()
    .find((message) => message.role === "agent" && message.type !== "welcome");

  if (!update) {
    return "No agent output yet. Start by describing your project in one paragraph.";
  }

  switch (update.type) {
    case "phase_transition":
      return `Phase moved from ${PHASE_LABELS[update.fromPhase]} to ${PHASE_LABELS[update.toPhase]}.`;
    case "interview_question":
      return `Interview question ${update.questionNum}/${update.totalInSection} is waiting for your answer.`;
    case "draft_review":
      return `${update.sectionName} draft v${update.version} is ready for your review.`;
    case "compliance_report":
      return `Compliance check finished: ${update.failed.length} failures and ${update.warnings.length} warnings.`;
    case "learning_summary":
      return `Past proposal analysis loaded (${update.outcome}).`;
    case "challenge":
      return `A reviewer-style challenge was generated in ${update.category}.`;
    case "text":
      return update.content;
    default:
      return "The assistant updated your workspace.";
  }
}

export default function WorkflowTransparencyDeck({ onAction }: WorkflowTransparencyDeckProps) {
  const [expanded, setExpanded] = useState(false);
  const phase = useProposalStore((s) => s.session.currentPhase);
  const interview = useProposalStore((s) => s.interview);
  const sections = useProposalStore((s) => s.proposalSections);
  const validation = useProposalStore((s) => s.validation);
  const requirementsFetched = useProposalStore((s) => s.requirements.fetched);
  const learnings = useProposalStore((s) => s.learnings);
  const messages = useProposalStore((s) => s.messages);

  const completedPhases = phase - 1;
  const phaseProgress = Math.round((completedPhases / 6) * 100);

  const totalInterviewQuestions = useMemo(() => TOTAL_INTERVIEW_QUESTIONS, []);
  const answeredInterviewQuestions = deriveInterviewAnsweredCount(interview);

  const interviewProgress =
    totalInterviewQuestions > 0
      ? Math.round((answeredInterviewQuestions / totalInterviewQuestions) * 100)
      : 0;

  const draftedSections = SECTION_ORDER.filter((sectionKey) => sections[sectionKey].draft !== null).length;
  const approvedSections = SECTION_ORDER.filter((sectionKey) => sections[sectionKey].approved).length;
  const draftProgress = Math.round((draftedSections / SECTION_ORDER.length) * 100);

  const learningsCount =
    learnings.successfulPatterns.length +
    learnings.weaknesses.length +
    learnings.reviewerConcerns.length;

  const processItems: ProcessItem[] = [
    {
      id: "requirements",
      label: "Requirement extraction",
      detail: requirementsFetched ? "ISF rules loaded" : "Waiting for requirement pull",
      progress: requirementsFetched ? 100 : phase >= 2 ? 55 : 0,
      state: requirementsFetched ? "complete" : phase >= 2 ? "running" : "queued",
    },
    {
      id: "learning",
      label: "Past proposal learning",
      detail: learningsCount > 0 ? `${learningsCount} reusable insights captured` : "No prior submissions parsed",
      progress: learningsCount > 0 ? 100 : phase === 3 ? 45 : 0,
      state: learningsCount > 0 ? "complete" : phase === 3 ? "running" : "queued",
    },
    {
      id: "interview",
      label: "Interview synthesis",
      detail: `${answeredInterviewQuestions}/${totalInterviewQuestions} questions answered`,
      progress: interviewProgress,
      state:
        interviewProgress === 100
          ? "complete"
          : phase >= 4
          ? "running"
          : "queued",
    },
    {
      id: "draft",
      label: "Draft assembly",
      detail: `${draftedSections}/${SECTION_ORDER.length} sections drafted`,
      progress: draftProgress,
      state:
        draftProgress === 100
          ? "complete"
          : phase >= 5
          ? "running"
          : "queued",
    },
    {
      id: "compliance",
      label: "Compliance scan",
      detail: validation.lastRun
        ? `${validation.failed.length} failed, ${validation.warnings.length} warnings`
        : "No validation run yet",
      progress: validation.lastRun ? 100 : phase === 6 ? 70 : 0,
      state: validation.lastRun
        ? validation.failed.length > 0
          ? "attention"
          : "complete"
        : phase === 6
        ? "running"
        : "queued",
    },
  ];

  const submissions: SubmissionItem[] = [
    {
      id: "abstract",
      label: "Abstract section",
      state: sections.abstract.approved
        ? "ready"
        : sections.abstract.draft
        ? "in_progress"
        : "missing",
      helper: sections.abstract.approved
        ? "Approved"
        : sections.abstract.draft
        ? "Draft awaiting approval"
        : "Not started",
    },
    {
      id: "proposal",
      label: "Full proposal draft",
      state:
        approvedSections === SECTION_ORDER.length
          ? "ready"
          : draftedSections > 0
          ? "in_progress"
          : "missing",
      helper: `${approvedSections}/${SECTION_ORDER.length} sections approved`,
    },
    {
      id: "compliance",
      label: "Compliance report",
      state: validation.lastRun
        ? validation.failed.length === 0
          ? "ready"
          : "blocked"
        : "missing",
      helper: validation.lastRun
        ? validation.failed.length === 0
          ? "Ready for submission"
          : `${validation.failed.length} blockers to resolve`
        : "Pending first validation run",
    },
    {
      id: "final",
      label: "Final submission package",
      state: validation.readyForSubmission ? "ready" : phase === 7 ? "in_progress" : "missing",
      helper: validation.readyForSubmission
        ? "Assemble and export"
        : phase === 7
        ? "Final assembly in progress"
        : "Starts in Phase 7",
    },
  ];

  const latestAgentUpdate = getLatestAgentUpdate(messages);

  if (!expanded) {
    return (
      <section className="mx-4 mt-3 flex-shrink-0 rounded-xl border border-[#d8cab8]/90 bg-white/90 shadow-[0_12px_28px_-26px_rgba(47,41,36,0.52)]">
        <div className="flex items-center justify-between gap-3 px-3 py-2.5 sm:px-4">
          <div className="flex min-w-0 items-center gap-2 text-xs text-[#5b4d3e]">
            <Radar size={12} className="text-[#8e623c]" />
            <span className="truncate">
              Phase {phase}: {PHASE_LABELS[phase]} - {phaseProgress}% complete
            </span>
          </div>
          <button
            onClick={() => setExpanded(true)}
            className="inline-flex items-center gap-1 rounded-md border border-[#d4c4ae] bg-white px-2.5 py-1 text-xs font-medium text-[#5b4d3f] transition-colors hover:bg-[#f7efe3]"
          >
            Open dashboard
            <ChevronDown size={12} />
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="mx-4 mt-3 flex-shrink-0 rounded-2xl border border-[#d8cab8]/90 bg-gradient-to-br from-white via-[#f9f3ea] to-[#f1e8dc] shadow-[0_18px_45px_-30px_rgba(47,41,36,0.45)]">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[#e2d5c5] px-4 py-3 sm:px-5">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#876447]">Granite Command Deck</p>
          <h2 className="font-display mt-0.5 text-base text-[#2f2924]">Transparent process view</h2>
        </div>
        <button
          onClick={() => setExpanded(false)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[#d4c4ae] bg-white px-3 py-1.5 text-xs font-medium text-[#5b4d3f] transition-colors hover:bg-[#f7efe3]"
        >
          Hide details
          <ChevronUp size={14} />
        </button>
      </div>

      <div className="max-h-[34vh] space-y-4 overflow-y-auto px-4 pb-4 pt-3 sm:px-5 sm:pb-5 sm:pt-4">
        <div className="rounded-xl border border-[#d8c9b5] bg-white/90 p-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="inline-flex items-center gap-2 rounded-full bg-[#f3e4d2] px-3 py-1 text-xs font-semibold text-[#8b623d]">
              <Radar size={13} />
              Phase {phase}: {PHASE_LABELS[phase]}
            </div>
            <div className="text-xs text-[#756351]">Overall completion: {phaseProgress}%</div>
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-[#ddd0c1]">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#ab7d51] via-[#8f7d69] to-[#68747d] transition-all"
              style={{ width: `${Math.max(phaseProgress, 6)}%` }}
            />
          </div>
        </div>

        <div className="grid gap-3 xl:grid-cols-3">
            <article className="rounded-xl border border-[#d8c9b5] bg-white p-4">
              <div className="mb-3 flex items-center gap-2 text-[#352d26]">
                <Bot size={16} className="text-[#8b623d]" />
                <h3 className="text-sm font-semibold">Latest AI update</h3>
              </div>
              <p className="text-sm leading-relaxed text-[#665646]">{latestAgentUpdate}</p>
              <button
                onClick={() => onAction("explain-current-step")}
                className="mt-3 inline-flex items-center gap-1.5 rounded-lg border border-[#d7c6b0] bg-[#f8eee1] px-3 py-1.5 text-xs font-semibold text-[#6c533f] transition-colors hover:bg-[#f2e3cf]"
              >
                <Sparkles size={13} />
                Explain this in plain language
              </button>
            </article>

            <article className="rounded-xl border border-[#d8c9b5] bg-white p-4">
              <div className="mb-3 flex items-center gap-2 text-[#352d26]">
                <Activity size={16} className="text-[#66727d]" />
                <h3 className="text-sm font-semibold">Ongoing processes</h3>
              </div>
              <div className="space-y-2.5">
                {processItems.map((item) => {
                  const StatusIcon = processIcon(item.state);
                  return (
                    <div key={item.id} className="rounded-lg bg-[#f8f2e8] p-2.5">
                      <div className="mb-1 flex items-center justify-between gap-2">
                        <div className="min-w-0">
                          <p className="truncate text-xs font-semibold text-[#3f342b]">{item.label}</p>
                          <p className="truncate text-xs text-[#746351]">{item.detail}</p>
                        </div>
                        <span
                          className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold ${processStyles(item.state)}`}
                        >
                          <StatusIcon size={10} />
                          {processLabel(item.state)}
                        </span>
                      </div>
                      <div className="h-1.5 overflow-hidden rounded-full bg-[#ddd0c1]">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-[#6b7781] to-[#ab7d51] transition-all"
                          style={{ width: `${Math.max(item.progress, 4)}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </article>

            <article className="rounded-xl border border-[#d8c9b5] bg-white p-4">
              <div className="mb-3 flex items-center gap-2 text-[#352d26]">
                <FileUp size={16} className="text-[#8b623d]" />
                <h3 className="text-sm font-semibold">Submission board</h3>
              </div>
              <div className="space-y-2.5">
                {submissions.map((item) => (
                  <div key={item.id} className="rounded-lg border border-[#deceb9] p-2.5">
                    <div className="mb-1 flex items-center justify-between gap-2">
                      <p className="text-xs font-semibold text-[#3f342b]">{item.label}</p>
                      <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${submissionBadge(item.state)}`}>
                        {item.state === "in_progress"
                          ? "In progress"
                          : item.state === "ready"
                          ? "Ready"
                          : item.state === "blocked"
                          ? "Blocked"
                          : "Pending"}
                      </span>
                    </div>
                    <p className="text-xs text-[#746351]">{item.helper}</p>
                  </div>
                ))}
              </div>
            </article>
          </div>

        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => onAction("view-status")}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[#302922] px-3 py-1.5 text-xs font-semibold text-white transition-colors hover:bg-[#241f1a]"
          >
            <Gauge size={13} />
            Open Full Dashboard
          </button>
          <button
            onClick={() => onAction("open-draft")}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#d4c4ae] bg-white px-3 py-1.5 text-xs font-semibold text-[#5a4c3f] transition-colors hover:bg-[#f7efe3]"
          >
            <ClipboardCheck size={13} />
            Review Draft Artifacts
          </button>
          <button
            onClick={() => onAction("view-report")}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#d4c4ae] bg-white px-3 py-1.5 text-xs font-semibold text-[#5a4c3f] transition-colors hover:bg-[#f7efe3]"
          >
            <Send size={13} />
            Check Submission Readiness
          </button>
        </div>
      </div>
    </section>
  );
}
