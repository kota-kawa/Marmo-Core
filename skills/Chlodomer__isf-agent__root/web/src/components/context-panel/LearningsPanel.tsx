"use client";

import { useState } from "react";
import { Upload } from "lucide-react";
import { useProposalStore } from "@/lib/store";

type SubTab = "patterns" | "weaknesses" | "concerns";

export default function LearningsPanel() {
  const learnings = useProposalStore((s) => s.learnings);
  const [activeTab, setActiveTab] = useState<SubTab>("patterns");

  const isEmpty =
    learnings.successfulPatterns.length === 0 &&
    learnings.weaknesses.length === 0 &&
    learnings.reviewerConcerns.length === 0;

  if (isEmpty) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center h-64">
        <p className="text-sm text-gray-500 leading-relaxed mb-4">
          No past proposals analyzed yet. Uploading past proposals helps the
          agent learn what works for you and what reviewers look for.
        </p>
        <button className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-md border border-purple-200 bg-purple-50 text-purple-700 hover:bg-purple-100 transition-colors">
          <Upload size={14} />
          Upload Past Proposal
        </button>
      </div>
    );
  }

  const tabs: { id: SubTab; label: string; count: number }[] = [
    { id: "patterns", label: "Patterns", count: learnings.successfulPatterns.length },
    { id: "weaknesses", label: "Weaknesses", count: learnings.weaknesses.length },
    { id: "concerns", label: "Concerns", count: learnings.reviewerConcerns.length },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="flex border-b border-gray-100 px-4">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-3 py-2 text-xs font-medium transition-colors ${
              activeTab === tab.id
                ? "text-purple-600 border-b-2 border-purple-600"
                : "text-gray-500 hover:text-gray-700"
            }`}
          >
            {tab.label} ({tab.count})
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {activeTab === "patterns" &&
          learnings.successfulPatterns.map((p) => (
            <div key={p.id} className="p-3 bg-emerald-50/50 rounded-md border border-emerald-100">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono text-emerald-600">{p.id}</span>
                <span className="text-xs px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-700">
                  {p.category}
                </span>
              </div>
              <p className="text-sm text-gray-700">{p.description}</p>
              <p className="text-xs text-gray-400 mt-1">
                {p.appliedTo
                  ? `Applied to: ${p.appliedTo}`
                  : "Not yet applied"}
              </p>
            </div>
          ))}

        {activeTab === "weaknesses" &&
          learnings.weaknesses.map((w) => (
            <div key={w.id} className="p-3 bg-red-50/50 rounded-md border border-red-100">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-mono text-red-600">{w.id}</span>
                <span className="text-xs px-1.5 py-0.5 rounded bg-red-100 text-red-700">
                  {w.category}
                </span>
              </div>
              <p className="text-sm text-gray-700">{w.description}</p>
              <p className="text-xs italic text-gray-500 mt-1">{w.prevention}</p>
            </div>
          ))}

        {activeTab === "concerns" &&
          learnings.reviewerConcerns.map((c, i) => (
            <div key={i} className="p-3 bg-amber-50/50 rounded-md border border-amber-100">
              <div className="flex items-center gap-2 mb-1">
                <span
                  className={`text-xs px-1.5 py-0.5 rounded ${
                    c.severity === "critical"
                      ? "bg-red-100 text-red-700"
                      : "bg-amber-100 text-amber-700"
                  }`}
                >
                  {c.severity}
                </span>
                <span className="text-xs text-gray-400">
                  Mentioned {c.frequency}x
                </span>
              </div>
              <p className="text-sm text-gray-700">{c.concern}</p>
              <p className="text-xs text-gray-500 mt-1">{c.prevention}</p>
            </div>
          ))}
      </div>
    </div>
  );
}
