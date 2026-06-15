"use client";

import { useState } from "react";
import { Check, ChevronDown, ChevronRight, Download, Minus } from "lucide-react";
import { useProposalStore } from "@/lib/store";
import { SECTION_ORDER, SECTION_LABELS, type SectionName } from "@/lib/types";
import {
  buildCompiledProposalPreview,
  getSectionLimitInfo,
} from "@/lib/workflow-sync";

export default function DraftViewerPanel() {
  const sections = useProposalStore((s) => s.proposalSections);
  const setSectionApproval = useProposalStore((s) => s.setSectionApproval);
  const [expanded, setExpanded] = useState<SectionName | null>(null);
  const [mode, setMode] = useState<"sections" | "compiled">("sections");

  const hasDrafts = SECTION_ORDER.some((k) => sections[k].draft !== null);

  if (!hasDrafts) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center h-64">
        <p className="text-sm text-gray-500 leading-relaxed">
          Your proposal will appear here as we build it together. Once we have
          enough information, the Abstract will be drafted first.
        </p>
      </div>
    );
  }

  const approvedCount = SECTION_ORDER.filter((k) => sections[k].approved).length;
  const totalEstPages = SECTION_ORDER.reduce((sum, k) => {
    const s = sections[k];
    return sum + (s.pageCount ?? (s.wordCount ? s.wordCount / 350 : 0));
  }, 0);
  const totalWords = SECTION_ORDER.reduce(
    (sum, key) => sum + (sections[key].wordCount ?? 0),
    0
  );
  const compiledPreview = buildCompiledProposalPreview(sections);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <h3 className="text-xs font-semibold text-gray-700 uppercase">Proposal Draft</h3>
        <button className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition-colors">
          <Download size={12} />
          Export PDF
        </button>
      </div>

      <div className="px-4 py-2 border-b border-gray-100">
        <div className="inline-flex rounded-lg border border-gray-200 bg-gray-50 p-0.5">
          <button
            onClick={() => setMode("sections")}
            className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
              mode === "sections"
                ? "bg-white text-gray-700 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Sections
          </button>
          <button
            onClick={() => setMode("compiled")}
            className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
              mode === "compiled"
                ? "bg-white text-gray-700 shadow-sm"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            Compiled Preview
          </button>
        </div>
      </div>

      {mode === "sections" ? (
        <div className="flex-1 overflow-y-auto">
          {SECTION_ORDER.map((key) => {
            const section = sections[key];
            const isExpanded = expanded === key;
            const isApproved = section.approved;
            const hasDraft = section.draft !== null;
            const wordCount = section.wordCount ?? 0;
            const charCount = section.charCount ?? section.draft?.length ?? 0;
            const limitInfo = getSectionLimitInfo(key, wordCount);

            return (
              <div key={key} className="border-b border-gray-50">
                <button
                  onClick={() => setExpanded(isExpanded ? null : key)}
                  className="w-full flex items-center gap-2 px-4 py-3 hover:bg-gray-50 transition-colors text-left"
                  disabled={!hasDraft}
                >
                  <div className="flex-shrink-0">
                    {isApproved ? (
                      <Check size={14} className="text-emerald-500" />
                    ) : hasDraft ? (
                      isExpanded ? (
                        <ChevronDown size={14} className="text-blue-500" />
                      ) : (
                        <ChevronRight size={14} className="text-blue-500" />
                      )
                    ) : (
                      <Minus size={14} className="text-gray-300" />
                    )}
                  </div>

                  <span
                    className={`text-sm flex-1 ${
                      isApproved
                        ? "text-emerald-700"
                        : hasDraft
                        ? "text-gray-700"
                        : "text-gray-400"
                    }`}
                  >
                    {SECTION_LABELS[key]}
                  </span>

                  <span
                    className={`text-xs px-2 py-0.5 rounded-full ${
                      isApproved
                        ? "bg-emerald-50 text-emerald-600"
                        : hasDraft
                        ? "bg-blue-50 text-blue-600"
                        : "bg-gray-50 text-gray-400"
                    }`}
                  >
                    {isApproved ? "Approved" : hasDraft ? "Draft ready" : "Not started"}
                  </span>
                </button>

                {isExpanded && hasDraft && (
                  <div className="px-4 pb-4">
                    <div className="bg-gray-50 rounded-md p-3 text-sm text-gray-700 leading-relaxed max-h-64 overflow-y-auto whitespace-pre-wrap">
                      {section.draft}
                    </div>
                    <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-gray-500">
                        {wordCount} words
                      </span>
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-gray-500">
                        {charCount} chars
                      </span>
                      {limitInfo.limit && (
                        <span
                          className={`rounded-full px-2 py-0.5 ${
                            limitInfo.tone === "over"
                              ? "bg-red-100 text-red-700"
                              : limitInfo.tone === "near"
                              ? "bg-amber-100 text-amber-700"
                              : "bg-emerald-100 text-emerald-700"
                          }`}
                        >
                          limit {limitInfo.limit} words
                        </span>
                      )}
                    </div>
                    <div className="mt-2 flex gap-2">
                      <button
                        onClick={() => setSectionApproval(key, true)}
                        className="rounded-md border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700 hover:bg-emerald-100"
                      >
                        Approve section
                      </button>
                      <button
                        onClick={() => setSectionApproval(key, false)}
                        className="rounded-md border border-gray-200 bg-white px-2.5 py-1 text-xs font-medium text-gray-600 hover:bg-gray-50"
                      >
                        Request changes
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-4">
          {compiledPreview ? (
            <div className="rounded-md border border-gray-200 bg-gray-50 p-3 text-sm leading-relaxed whitespace-pre-wrap text-gray-700">
              {compiledPreview}
            </div>
          ) : (
            <p className="text-sm text-gray-500">
              No compiled preview yet. Draft at least one section to build it.
            </p>
          )}
        </div>
      )}

      <div className="px-4 py-3 border-t border-gray-100 text-xs text-gray-400">
        {approvedCount}/{SECTION_ORDER.length} sections approved
        &middot; {totalWords.toLocaleString()} words
        &middot; ~{totalEstPages.toFixed(1)} pages
      </div>
    </div>
  );
}
