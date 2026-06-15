"use client";

import Image from "next/image";
import { useProposalStore } from "@/lib/store";
import type { Phase } from "@/lib/types";
import PhaseStepper from "./PhaseStepper";
import QuickActions from "./QuickActions";
import SessionMeta from "./SessionMeta";
import { Gauge, Sparkles } from "lucide-react";

interface LeftRailProps {
  onPhaseClick: (phase: Phase) => void;
  onAction: (action: string) => void;
}

export default function LeftRail({ onPhaseClick, onAction }: LeftRailProps) {
  const title = useProposalStore((s) => s.projectInfo.title);
  const phase = useProposalStore((s) => s.session.currentPhase);
  const completionPercent = Math.round(((phase - 1) / 6) * 100);

  return (
    <aside className="w-full lg:w-[17rem] xl:w-[18rem] max-h-[38vh] lg:max-h-none flex-shrink-0 bg-gradient-to-b from-white/92 via-[#f8f3ec]/88 to-[#f3ece2]/88 border border-[#ddcfbd] rounded-2xl shadow-[0_20px_46px_-34px_rgba(47,41,36,0.5)] flex flex-col h-auto lg:h-full overflow-hidden">
      {/* Session header */}
      <div className="px-4 py-4 border-b border-[#e6d9c8] bg-gradient-to-br from-white via-[#f4ecdf] to-[#ece5db]">
        <div className="mb-3 flex items-center gap-2">
          <Image
            src="/granite-logo.png"
            alt="Granite logo"
            width={24}
            height={24}
            className="h-6 w-6 rounded-md object-cover"
          />
          <p className="text-xs font-semibold uppercase tracking-[0.12em] text-[#6f5a44]">Granite</p>
        </div>
        <h1 className="font-display text-base font-semibold text-[#2f2924] truncate">
          {title || "New Proposal"}
        </h1>
        <p className="text-xs text-[#7c6a58] mt-0.5">ISF Personal Research Grant</p>

        <div className="mt-3 rounded-lg border border-[#d9c9b4] bg-white p-2.5">
          <div className="flex items-center justify-between gap-2 text-xs mb-2">
            <span className="inline-flex items-center gap-1.5 text-[#8b623d] font-semibold">
              <Gauge size={12} />
              Process visibility
            </span>
            <span className="text-[#7c6855]">{completionPercent}%</span>
          </div>
          <div className="w-full h-1.5 rounded-full bg-[#dfd2c3] overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#ab7e52] to-[#6b7781] transition-all"
              style={{ width: `${Math.max(completionPercent, 5)}%` }}
            />
          </div>
          <button
            onClick={() => onAction("view-status")}
            className="mt-2 w-full inline-flex items-center justify-center gap-1.5 rounded-md bg-[#312a24] px-2.5 py-1.5 text-xs font-semibold text-white hover:bg-[#241f1b] transition-colors"
          >
            <Sparkles size={12} />
            Open operations dashboard
          </button>
        </div>
      </div>

      {/* Phase stepper */}
      <PhaseStepper onPhaseClick={onPhaseClick} />

      {/* Divider */}
      <div className="border-t border-[#e6d9c8]" />

      {/* Quick actions */}
      <QuickActions onAction={onAction} />

      {/* Session metadata */}
      <SessionMeta />
    </aside>
  );
}
