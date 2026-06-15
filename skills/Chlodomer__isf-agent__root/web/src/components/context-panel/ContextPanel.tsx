"use client";

import { X } from "lucide-react";
import { useProposalStore } from "@/lib/store";
import PanelTabs from "./PanelTabs";
import DraftViewerPanel from "./DraftViewerPanel";
import LearningsPanel from "./LearningsPanel";
import ComplianceDashboardPanel from "./ComplianceDashboardPanel";
import InterviewTrackerPanel from "./InterviewTrackerPanel";
import OperationsDashboardPanel from "./OperationsDashboardPanel";
import SubmissionReadinessPanel from "./SubmissionReadinessPanel";
import VersionHistoryPanel from "./VersionHistoryPanel";

interface ContextPanelProps {
  onAction?: (action: string) => void;
}

export default function ContextPanel({ onAction }: ContextPanelProps) {
  const activeTab = useProposalStore((s) => s.ui.activeContextTab);
  const toggleContextPanel = useProposalStore((s) => s.toggleContextPanel);

  return (
    <aside className="w-full max-h-[48vh] lg:max-h-none lg:w-[380px] flex-shrink-0 bg-white/95 backdrop-blur-sm border-t lg:border-t-0 lg:border-l border-slate-200 shadow-[0_-12px_30px_-20px_rgba(0,0,0,0.35)] lg:shadow-lg flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100">
        <PanelTabs />
        <button
          onClick={toggleContextPanel}
          className="p-1 text-slate-400 hover:text-slate-700 transition-colors rounded"
          aria-label="Close panel"
        >
          <X size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-hidden">
        {activeTab === "operations" && <OperationsDashboardPanel />}
        {activeTab === "readiness" && <SubmissionReadinessPanel onAction={onAction} />}
        {activeTab === "history" && <VersionHistoryPanel />}
        {activeTab === "draft" && <DraftViewerPanel />}
        {activeTab === "learnings" && <LearningsPanel />}
        {activeTab === "compliance" && <ComplianceDashboardPanel onAction={onAction} />}
        {activeTab === "interview" && <InterviewTrackerPanel />}
      </div>
    </aside>
  );
}
