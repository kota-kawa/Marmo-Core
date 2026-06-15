"use client";

import { ArrowRight, Eye } from "lucide-react";
import { PHASE_LABELS, type Phase } from "@/lib/types";

interface ResumeSessionCardProps {
  proposalTitle: string | null;
  currentPhase: Phase;
  completedPhases: Phase[];
  lastActive: string;
  onAction?: (action: string) => void;
}

export default function ResumeSessionCard({
  proposalTitle,
  currentPhase,
  completedPhases,
  lastActive,
  onAction,
}: ResumeSessionCardProps) {
  const remainingPhases = ([1, 2, 3, 4, 5, 6, 7] as Phase[]).filter(
    (p) => !completedPhases.includes(p) && p !== currentPhase
  );

  return (
    <div className="my-4 bg-white rounded-lg border border-gray-200 shadow-sm">
      <div className="p-5">
        <h3 className="text-lg font-semibold text-gray-900 mb-1">Welcome back!</h3>
        <p className="text-sm text-gray-500 mb-4">Last active: {lastActive}</p>

        {proposalTitle && (
          <p className="text-sm text-gray-700 mb-4">
            <span className="font-medium">Proposal:</span> {proposalTitle}
          </p>
        )}

        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <p className="text-xs font-medium text-gray-500 uppercase mb-2">Completed</p>
            <ul className="space-y-1">
              {completedPhases.map((p) => (
                <li key={p} className="text-sm text-emerald-600 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
                  {PHASE_LABELS[p]}
                </li>
              ))}
            </ul>
          </div>

          <div>
            <p className="text-xs font-medium text-gray-500 uppercase mb-2">Remaining</p>
            <ul className="space-y-1">
              <li className="text-sm text-teal-700 font-medium flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-teal-500" />
                {PHASE_LABELS[currentPhase]} (current)
              </li>
              {remainingPhases.map((p) => (
                <li key={p} className="text-sm text-gray-400 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-gray-300" />
                  {PHASE_LABELS[p]}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <div className="flex gap-2 px-5 py-3 border-t border-gray-100 bg-gray-50/50 rounded-b-lg">
        <button
          onClick={() => onAction?.("continue")}
          className="text-sm px-4 py-1.5 rounded-md bg-teal-600 text-white hover:bg-teal-700 transition-colors flex items-center gap-1.5"
        >
          Continue Where I Left Off
          <ArrowRight size={14} />
        </button>
        <button
          onClick={() => onAction?.("view-status")}
          className="text-sm px-3 py-1.5 rounded-md border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 transition-colors flex items-center gap-1.5"
        >
          <Eye size={14} />
          View Full Status
        </button>
      </div>
    </div>
  );
}
