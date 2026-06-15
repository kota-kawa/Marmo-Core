"use client";

import { ArrowRight } from "lucide-react";
import { PHASE_LABELS, type Phase } from "@/lib/types";

interface PhaseTransitionCardProps {
  fromPhase: Phase;
  toPhase: Phase;
  summary: string;
  onAction?: (action: string) => void;
}

export default function PhaseTransitionCard({
  fromPhase,
  toPhase,
  summary,
  onAction,
}: PhaseTransitionCardProps) {
  return (
    <div className="my-4 bg-gradient-to-r from-teal-50 to-white rounded-lg border border-teal-200 shadow-sm">
      <div className="p-5">
        <h3 className="text-base font-semibold text-teal-800 mb-2">
          Phase {fromPhase} Complete: {PHASE_LABELS[fromPhase]}
        </h3>
        <p className="text-sm text-gray-600 leading-relaxed">{summary}</p>
      </div>

      <div className="flex gap-2 px-5 py-3 border-t border-teal-100">
        <button
          onClick={() => onAction?.("view-summary")}
          className="text-sm px-3 py-1.5 rounded-md border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 transition-colors"
        >
          View Summary
        </button>
        <button
          onClick={() => onAction?.(`go-phase:${toPhase}`)}
          className="text-sm px-4 py-1.5 rounded-md bg-teal-600 text-white hover:bg-teal-700 transition-colors flex items-center gap-1.5"
        >
          Continue to {PHASE_LABELS[toPhase]}
          <ArrowRight size={14} />
        </button>
      </div>
    </div>
  );
}
