"use client";

import { X, AlertTriangle } from "lucide-react";
import type { ComplianceIssue } from "@/lib/types";

interface ComplianceReportCardProps {
  passed: number;
  failed: ComplianceIssue[];
  warnings: ComplianceIssue[];
  onAction?: (action: string) => void;
}

export default function ComplianceReportCard({
  passed,
  failed,
  warnings,
  onAction,
}: ComplianceReportCardProps) {
  const hasFailures = failed.length > 0;
  const borderColor = hasFailures ? "border-l-red-500" : "border-l-emerald-500";

  return (
    <div className={`my-3 bg-white rounded-lg border border-gray-200 border-l-4 ${borderColor} shadow-sm`}>
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wide text-gray-700">
            Compliance Check Results
          </span>
          <span
            className={`text-xs font-medium px-2 py-0.5 rounded-full ${
              hasFailures
                ? "bg-red-50 text-red-700"
                : "bg-emerald-50 text-emerald-700"
            }`}
          >
            {hasFailures ? `${failed.length} Issues Found` : "All Passed"}
          </span>
        </div>

        <div className="flex gap-4 text-sm mb-4">
          <span className="text-emerald-600 font-medium">Passed: {passed}</span>
          <span className="text-red-600 font-medium">Failed: {failed.length}</span>
          <span className="text-amber-600 font-medium">Warnings: {warnings.length}</span>
        </div>

        {failed.length > 0 && (
          <div className="space-y-2 mb-3">
            <p className="text-xs font-medium text-red-600 uppercase">Must Fix</p>
            {failed.map((issue) => (
              <div key={issue.id} className="flex items-start gap-2 text-sm">
                <X size={14} className="text-red-500 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <span className="font-medium text-gray-700">{issue.id}:</span>{" "}
                  <span className="text-gray-600">{issue.description}</span>
                  <button
                    onClick={() => onAction?.(`fix:${issue.id}`)}
                    className="ml-2 text-xs text-blue-600 hover:text-blue-700 underline"
                  >
                    Fix in chat
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {warnings.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-amber-600 uppercase">Warnings</p>
            {warnings.map((issue) => (
              <div key={issue.id} className="flex items-start gap-2 text-sm">
                <AlertTriangle size={14} className="text-amber-500 mt-0.5 flex-shrink-0" />
                <div>
                  <span className="font-medium text-gray-700">{issue.id}:</span>{" "}
                  <span className="text-gray-600">{issue.description}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="flex gap-2 px-4 py-3 border-t border-gray-100 bg-gray-50/50 rounded-b-lg">
        <button
          onClick={() => onAction?.("view-report")}
          className="text-sm px-3 py-1.5 rounded-md border border-gray-200 bg-white text-gray-600 hover:bg-gray-50 transition-colors"
        >
          View Full Report
        </button>
        {hasFailures && (
          <button
            onClick={() => onAction?.("fix-issues")}
            className="text-sm px-3 py-1.5 rounded-md border border-red-200 bg-red-50 text-red-700 hover:bg-red-100 transition-colors"
          >
            Fix Issues
          </button>
        )}
      </div>
    </div>
  );
}
