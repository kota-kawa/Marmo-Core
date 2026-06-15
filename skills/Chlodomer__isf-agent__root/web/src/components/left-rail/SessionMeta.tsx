"use client";

import { Clock, Calendar } from "lucide-react";
import { useProposalStore } from "@/lib/store";

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return "Not saved yet";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function daysUntil(dateStr: string | null): number | null {
  if (!dateStr) return null;
  const diff = new Date(dateStr).getTime() - Date.now();
  return Math.ceil(diff / (1000 * 60 * 60 * 24));
}

export default function SessionMeta() {
  const lastUpdated = useProposalStore((s) => s.session.lastUpdated);
  const deadline = useProposalStore((s) => s.requirements.deadline);
  const daysLeft = daysUntil(deadline);

  return (
    <div className="px-3 py-3 border-t border-gray-100 space-y-1.5">
      <div className="flex items-center gap-2 text-xs text-gray-400">
        <Clock size={12} />
        <span>Last saved: {formatRelativeTime(lastUpdated)}</span>
      </div>

      {deadline && daysLeft !== null && (
        <div
          className={`flex items-center gap-2 text-xs ${
            daysLeft <= 7 ? "text-red-500" : daysLeft <= 30 ? "text-amber-500" : "text-gray-400"
          }`}
        >
          <Calendar size={12} />
          <span>
            Deadline: {new Date(deadline).toLocaleDateString("en-IL", { month: "short", day: "numeric", year: "numeric" })}
            {daysLeft > 0 && ` (${daysLeft}d left)`}
          </span>
        </div>
      )}
    </div>
  );
}
