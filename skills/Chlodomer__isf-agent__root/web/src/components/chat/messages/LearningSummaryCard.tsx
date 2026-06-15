"use client";

import type { SuccessfulPattern, Weakness, RedFlag } from "@/lib/types";

interface LearningSummaryCardProps {
  proposalName: string;
  outcome: "funded" | "rejected";
  patterns?: SuccessfulPattern[];
  weaknesses?: Weakness[];
  redFlags?: RedFlag[];
  onAction?: (action: string) => void;
}

export default function LearningSummaryCard({
  proposalName,
  outcome,
  patterns,
  weaknesses,
  redFlags,
  onAction,
}: LearningSummaryCardProps) {
  return (
    <div className="my-3 bg-white rounded-lg border border-gray-200 border-l-4 border-l-purple-500 shadow-sm">
      <div className="p-4">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs font-semibold uppercase tracking-wide text-purple-700">
            Learnings: {proposalName}
          </span>
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full ${
              outcome === "funded"
                ? "bg-emerald-50 text-emerald-700"
                : "bg-red-50 text-red-700"
            }`}
          >
            {outcome === "funded" ? "Funded" : "Rejected"}
          </span>
        </div>

        {patterns && patterns.length > 0 && (
          <div className="mb-3">
            <p className="text-sm font-medium text-gray-700 mb-1">
              Patterns Found: {patterns.length}
            </p>
            <ul className="space-y-0.5">
              {patterns.map((p) => (
                <li key={p.id} className="text-sm text-gray-600 flex items-start gap-1.5">
                  <span className="text-emerald-500 mt-0.5">+</span>
                  {p.description}
                </li>
              ))}
            </ul>
          </div>
        )}

        {weaknesses && weaknesses.length > 0 && (
          <div className="mb-3">
            <p className="text-sm font-medium text-gray-700 mb-1">
              Weaknesses Found: {weaknesses.length}
            </p>
            <ul className="space-y-0.5">
              {weaknesses.map((w) => (
                <li key={w.id} className="text-sm text-gray-600 flex items-start gap-1.5">
                  <span className="text-red-500 mt-0.5">&minus;</span>
                  {w.description}
                </li>
              ))}
            </ul>
          </div>
        )}

        {redFlags && redFlags.length > 0 && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-1">
              Red Flag Phrases: {redFlags.length}
            </p>
            <ul className="space-y-0.5">
              {redFlags.map((rf, i) => (
                <li key={i} className="text-sm text-gray-600 flex items-start gap-1.5">
                  <span className="text-amber-500 mt-0.5">!</span>
                  <span>
                    &ldquo;{rf.phrase}&rdquo;{" "}
                    <span className="text-gray-400">&times;{rf.count}</span>{" "}
                    <span className="text-gray-400">({rf.problem})</span>
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="flex gap-2 px-4 py-3 border-t border-gray-100 bg-gray-50/50 rounded-b-lg">
        <button
          onClick={() => onAction?.("view-learnings")}
          className="text-sm px-3 py-1.5 rounded-md border border-purple-200 bg-purple-50 text-purple-700 hover:bg-purple-100 transition-colors"
        >
          View All Learnings
        </button>
        <button
          onClick={() => onAction?.("add-reviews")}
          className="text-sm px-3 py-1.5 rounded-md border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Add Reviewer Feedback
        </button>
      </div>
    </div>
  );
}
