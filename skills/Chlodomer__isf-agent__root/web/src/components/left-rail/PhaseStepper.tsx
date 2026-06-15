"use client";

import { useProposalStore } from "@/lib/store";
import { PHASE_LABELS, type Phase } from "@/lib/types";
import PhaseItem, { type PhaseStatus } from "./PhaseItem";
import SubProgress from "./SubProgress";

interface PhaseStepperProps {
  onPhaseClick: (phase: Phase) => void;
}

export default function PhaseStepper({ onPhaseClick }: PhaseStepperProps) {
  const currentPhase = useProposalStore((s) => s.session.currentPhase);

  function getStatus(phase: Phase): PhaseStatus {
    if (phase < currentPhase) return "completed";
    if (phase === currentPhase) return "active";
    return "upcoming";
  }

  return (
    <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
      {([1, 2, 3, 4, 5, 6, 7] as Phase[]).map((phase) => {
        const status = getStatus(phase);
        const hasSubProgress = phase === 4 || phase === 5;

        return (
          <PhaseItem
            key={phase}
            phase={phase}
            label={PHASE_LABELS[phase]}
            status={status}
            onClick={onPhaseClick}
          >
            {hasSubProgress ? <SubProgress phase={phase} /> : undefined}
          </PhaseItem>
        );
      })}
    </nav>
  );
}
