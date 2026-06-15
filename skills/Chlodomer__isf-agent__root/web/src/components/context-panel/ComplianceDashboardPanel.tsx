"use client";

import { X, AlertTriangle, RefreshCw } from "lucide-react";
import { useProposalStore } from "@/lib/store";

interface ComplianceDashboardPanelProps {
  onAction?: (action: string) => void;
}

export default function ComplianceDashboardPanel({ onAction }: ComplianceDashboardPanelProps) {
  const validation = useProposalStore((s) => s.validation);

  if (!validation.lastRun) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center h-64">
        <p className="text-sm text-gray-500 leading-relaxed mb-4">
          Compliance check will run after all sections are drafted. You can also
          run a partial check anytime to catch issues early.
        </p>
        <button
          onClick={() => onAction?.("/validate")}
          className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-md border border-teal-200 bg-teal-50 text-teal-700 hover:bg-teal-100 transition-colors"
        >
          <RefreshCw size={14} />
          Run Partial Check
        </button>
      </div>
    );
  }

  const total = validation.passed.length + validation.failed.length + validation.warnings.length;
  const passRate = total > 0 ? (validation.passed.length / total) * 100 : 0;

  // Group issues by category
  const failedByCategory = validation.failed.reduce((acc, issue) => {
    if (!acc[issue.category]) acc[issue.category] = [];
    acc[issue.category].push(issue);
    return acc;
  }, {} as Record<string, typeof validation.failed>);

  const warningsByCategory = validation.warnings.reduce((acc, issue) => {
    if (!acc[issue.category]) acc[issue.category] = [];
    acc[issue.category].push(issue);
    return acc;
  }, {} as Record<string, typeof validation.warnings>);

  const categories = new Set([
    ...Object.keys(failedByCategory),
    ...Object.keys(warningsByCategory),
  ]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-100">
        <h3 className="text-xs font-semibold text-gray-700 uppercase">
          Compliance Dashboard
        </h3>
        <button
          onClick={() => onAction?.("/validate")}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 transition-colors"
        >
          <RefreshCw size={14} />
          Re-run
        </button>
      </div>

      <div className="px-4 py-3 border-b border-gray-100">
        <div className="flex gap-4 text-sm mb-2">
          <span className="text-emerald-600 font-medium">
            Passed: {validation.passed.length}
          </span>
          <span className="text-red-600 font-medium">
            Failed: {validation.failed.length}
          </span>
          <span className="text-amber-600 font-medium">
            Warnings: {validation.warnings.length}
          </span>
        </div>
        <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full transition-all"
            style={{ width: `${passRate}%` }}
          />
        </div>
        <p className="text-xs text-gray-400 mt-1">{Math.round(passRate)}% passing</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {[...categories].map((cat) => {
          const catFailed = failedByCategory[cat] || [];
          const catWarnings = warningsByCategory[cat] || [];

          return (
            <div key={cat}>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs font-semibold text-gray-600 uppercase">
                  {cat}
                </span>
                {catFailed.length > 0 && (
                  <span className="text-xs text-red-500">
                    {catFailed.length} issue{catFailed.length > 1 ? "s" : ""}
                  </span>
                )}
              </div>

              <div className="space-y-1.5">
                {catFailed.map((issue) => (
                  <div key={issue.id} className="flex items-start gap-2 text-sm p-2 bg-red-50 rounded">
                    <X size={12} className="text-red-500 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <span className="font-mono text-xs text-red-600">{issue.id}</span>
                      <p className="text-xs text-gray-600">{issue.description}</p>
                    </div>
                    <button
                      onClick={() => onAction?.(`fix:${issue.id}`)}
                      className="text-xs text-blue-600 hover:underline flex-shrink-0"
                    >
                      Fix
                    </button>
                  </div>
                ))}

                {catWarnings.map((issue) => (
                  <div key={issue.id} className="flex items-start gap-2 text-sm p-2 bg-amber-50 rounded">
                    <AlertTriangle size={12} className="text-amber-500 mt-0.5 flex-shrink-0" />
                    <div>
                      <span className="font-mono text-xs text-amber-600">{issue.id}</span>
                      <p className="text-xs text-gray-600">{issue.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>

      {validation.failed.length > 0 && (
        <div className="px-4 py-3 border-t border-gray-100">
          <button
            onClick={() => onAction?.("fix-issues")}
            className="w-full text-sm py-2 rounded-md bg-red-50 text-red-700 border border-red-200 hover:bg-red-100 transition-colors"
          >
            Fix All Issues
          </button>
        </div>
      )}
    </div>
  );
}
