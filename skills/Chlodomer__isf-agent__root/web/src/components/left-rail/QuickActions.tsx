"use client";

import { Upload, BarChart3, HelpCircle, RotateCcw, ShieldCheck, Download, Settings } from "lucide-react";

interface QuickActionsProps {
  onAction: (action: string) => void;
}

export default function QuickActions({ onAction }: QuickActionsProps) {
  const actions = [
    { icon: Upload, label: "Upload Past Proposal", action: "upload" },
    { icon: BarChart3, label: "Open Dashboard", action: "view-status" },
    { icon: ShieldCheck, label: "Submission Readiness", action: "open-readiness" },
    { icon: Download, label: "Export My Data", action: "export-data" },
    { icon: HelpCircle, label: "Explain This Phase", action: "explain-current-step" },
    { icon: RotateCcw, label: "Replay Onboarding", action: "replay-onboarding" },
    { icon: Settings, label: "Chat Settings", action: "open-settings" },
  ];

  return (
    <div className="px-3 py-2 space-y-1.5">
      {actions.map(({ icon: Icon, label, action }) => (
        <button
          key={action}
          onClick={() => onAction(action)}
          className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-sm text-slate-600 hover:text-slate-900 hover:bg-slate-100 transition-colors"
        >
          <Icon size={15} />
          {label}
        </button>
      ))}
    </div>
  );
}
