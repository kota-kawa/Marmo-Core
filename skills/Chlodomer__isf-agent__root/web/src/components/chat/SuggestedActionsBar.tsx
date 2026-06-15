"use client";

import { useProposalStore } from "@/lib/store";
import { SECTION_ORDER } from "@/lib/types";
import { getSuggestedActions, type SuggestedAction } from "@/lib/chat-actions";

interface SuggestedActionsBarProps {
  onAction: (command: string) => void;
}

export default function SuggestedActionsBar({ onAction }: SuggestedActionsBarProps) {
  const phase = useProposalStore((s) => s.session.currentPhase);
  const proposalSections = useProposalStore((s) => s.proposalSections);
  const draftReady = SECTION_ORDER.some(
    (section) => Boolean(proposalSections[section].draft) && !proposalSections[section].approved
  );
  const actions = getSuggestedActions(phase, { draftReady });

  if (actions.length === 0) return null;

  return (
    <div className="flex gap-2 overflow-x-auto border-t border-[#ddcdb9] bg-gradient-to-r from-white via-[#faf4eb] to-[#f3ebe0] px-4 py-2.5">
      {actions.map((action: SuggestedAction) => (
        <button
          key={action.command}
          onClick={() => onAction(action.command)}
          className={`
            flex-shrink-0 text-[15px] px-3.5 py-2 rounded-full border transition-colors
            ${
              action.variant === "approve"
                ? "border-[#cfb18f] bg-[#f8ebd9] text-[#7c5636] hover:bg-[#f0dec5]"
                : "border-[#d7c5ad] bg-white/90 text-[#5d4f41] hover:bg-[#f8efe3] hover:text-[#473c31]"
            }
          `}
        >
          {action.label}
        </button>
      ))}
      <button
        onClick={() => onAction("show-welcome")}
        className="flex-shrink-0 rounded-full border border-[#d7c5ad] bg-white/90 px-3.5 py-2 text-[15px] text-[#5d4f41] transition-colors hover:bg-[#f8efe3] hover:text-[#473c31]"
      >
        Welcome Actions
      </button>
    </div>
  );
}
