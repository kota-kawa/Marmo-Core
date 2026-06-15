"use client";

import { X } from "lucide-react";
import { useState } from "react";

interface NextActionBannerProps {
  text: string;
  onContinue?: () => void;
}

export default function NextActionBanner({ text, onContinue }: NextActionBannerProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed || !text) return null;

  return (
    <div className="flex items-center gap-3 border-b border-[#dccdb9] bg-gradient-to-r from-[#f9f0e2] via-[#f5ebdf] to-[#eee6dc] px-4 py-3">
      <span className="flex-1 text-base text-[#5f4d3d]">
        <span className="font-medium">Next:</span> {text}
      </span>
      {onContinue && (
        <button
          onClick={onContinue}
          className="rounded-md bg-[#9a6f45] px-3 py-1.5 text-sm font-medium text-white transition-colors hover:bg-[#865f3c]"
        >
          Continue
        </button>
      )}
      <button
        onClick={() => setDismissed(true)}
        className="text-[#9f886f] transition-colors hover:text-[#7f674f]"
        aria-label="Dismiss"
      >
        <X size={14} />
      </button>
    </div>
  );
}
