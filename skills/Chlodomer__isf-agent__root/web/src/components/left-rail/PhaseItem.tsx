"use client";

import { Check, ChevronDown, ChevronRight, Circle } from "lucide-react";
import type { Phase } from "@/lib/types";

export type PhaseStatus = "completed" | "active" | "upcoming";

interface PhaseItemProps {
  phase: Phase;
  label: string;
  status: PhaseStatus;
  onClick: (phase: Phase) => void;
  children?: React.ReactNode; // SubProgress
}

export default function PhaseItem({
  phase,
  label,
  status,
  onClick,
  children,
}: PhaseItemProps) {
  return (
    <div className="relative">
      <button
        onClick={() => onClick(phase)}
        className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-md text-left transition-colors ${
          status === "active"
            ? "bg-teal-50 border-l-3 border-l-teal-600"
            : status === "completed"
            ? "hover:bg-gray-100"
            : "opacity-50 hover:opacity-70"
        }`}
      >
        <div className="flex-shrink-0 w-5 h-5 flex items-center justify-center">
          {status === "completed" ? (
            <div className="w-5 h-5 rounded-full bg-teal-100 flex items-center justify-center">
              <Check size={12} className="text-teal-600" />
            </div>
          ) : status === "active" ? (
            <div className="w-5 h-5 rounded-full bg-teal-600 flex items-center justify-center">
              <span className="text-[10px] font-bold text-white">{phase}</span>
            </div>
          ) : (
            <Circle size={16} className="text-gray-300" />
          )}
        </div>

        <span
          className={`text-sm flex-1 ${
            status === "active"
              ? "font-semibold text-teal-800"
              : status === "completed"
              ? "text-gray-500"
              : "text-gray-400"
          }`}
        >
          {label}
        </span>

        {children && status === "active" && (
          <ChevronDown size={14} className="text-teal-400" />
        )}
        {children && status !== "active" && (
          <ChevronRight size={14} className="text-gray-300" />
        )}
      </button>

      {children && status === "active" && (
        <div className="ml-10 mt-1 mb-2 space-y-0.5">{children}</div>
      )}
    </div>
  );
}
