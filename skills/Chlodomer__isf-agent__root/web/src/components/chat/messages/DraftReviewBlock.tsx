"use client";

import { Check } from "lucide-react";
import { SECTION_LABELS, type SectionName } from "@/lib/types";

interface DraftReviewBlockProps {
  sectionName: SectionName;
  version: number;
  wordCount: number;
  pageEstimate: number;
  patternsApplied: string[];
  concernsAddressed: string[];
  content: string;
  onAction?: (action: string) => void;
}

export default function DraftReviewBlock({
  sectionName,
  version,
  wordCount,
  pageEstimate,
  patternsApplied,
  concernsAddressed,
  onAction,
}: DraftReviewBlockProps) {
  const label = SECTION_LABELS[sectionName] ?? sectionName;

  return (
    <div className="my-3 bg-white rounded-lg border border-gray-200 border-l-4 border-l-blue-500 shadow-sm">
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wide text-blue-700">
            Draft: {label} (v{version})
          </span>
          <span className="text-xs text-gray-400">
            {wordCount.toLocaleString()} words &middot; ~{pageEstimate} pages
          </span>
        </div>

        {patternsApplied.length > 0 && (
          <div className="mb-2">
            <p className="text-xs font-medium text-gray-500 mb-1">Patterns applied:</p>
            <ul className="space-y-0.5">
              {patternsApplied.map((p, i) => (
                <li key={i} className="text-sm text-gray-600 flex items-start gap-1.5">
                  <Check size={12} className="text-emerald-500 mt-0.5 flex-shrink-0" />
                  {p}
                </li>
              ))}
            </ul>
          </div>
        )}

        {concernsAddressed.length > 0 && (
          <div>
            <p className="text-xs font-medium text-gray-500 mb-1">Verified against:</p>
            <ul className="space-y-0.5">
              {concernsAddressed.map((c, i) => (
                <li key={i} className="text-sm text-gray-600 flex items-start gap-1.5">
                  <Check size={12} className="text-blue-500 mt-0.5 flex-shrink-0" />
                  {c}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="flex gap-2 px-4 py-3 border-t border-gray-100 bg-gray-50/50 rounded-b-lg">
        <button
          onClick={() => onAction?.("open-draft")}
          className="text-sm px-3 py-1.5 rounded-md border border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 transition-colors"
        >
          Open Full Draft
        </button>
        <button
          onClick={() => onAction?.(`approve:${sectionName}`)}
          className="text-sm px-3 py-1.5 rounded-md border border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 transition-colors flex items-center gap-1"
        >
          <Check size={14} /> Approve
        </button>
        <button
          onClick={() => onAction?.(`request-changes:${sectionName}`)}
          className="text-sm px-3 py-1.5 rounded-md border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 transition-colors"
        >
          Request Changes
        </button>
      </div>
    </div>
  );
}
