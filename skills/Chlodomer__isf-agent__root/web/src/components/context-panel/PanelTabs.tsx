"use client";

import { useProposalStore } from "@/lib/store";
import type { ContextTab } from "@/lib/types";

const TABS: { id: ContextTab; label: string }[] = [
  { id: "operations", label: "Operations" },
  { id: "readiness", label: "Readiness" },
  { id: "history", label: "History" },
  { id: "draft", label: "Draft" },
  { id: "learnings", label: "Learnings" },
  { id: "compliance", label: "Compliance" },
  { id: "interview", label: "Interview" },
];

export default function PanelTabs() {
  const activeTab = useProposalStore((s) => s.ui.activeContextTab);
  const setContextTab = useProposalStore((s) => s.setContextTab);

  return (
    <div className="flex border-b border-slate-200 overflow-x-auto">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => setContextTab(tab.id)}
          className={`flex-shrink-0 px-3 py-2.5 text-sm font-medium transition-colors ${
            activeTab === tab.id
              ? "text-teal-700 border-b-2 border-teal-600"
              : "text-slate-500 hover:text-slate-700"
          }`}
        >
          {tab.label}
        </button>
      ))}
    </div>
  );
}
