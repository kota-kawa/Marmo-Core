"use client";

import { Database, X } from "lucide-react";

interface ChatPersistenceBannerProps {
  onAccept: () => void;
  onDismiss: () => void;
}

export default function ChatPersistenceBanner({
  onAccept,
  onDismiss,
}: ChatPersistenceBannerProps) {
  return (
    <div className="mx-4 mb-2 rounded-xl border border-[#d1c4b0] bg-[#fdf8f1] px-4 py-3 flex items-start gap-3">
      <Database
        size={18}
        className="text-[#8b6e50] mt-0.5 flex-shrink-0"
      />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-[#3f342b]">
          Save chat history to your account?
        </p>
        <p className="text-xs text-[#6d5841] mt-1 leading-relaxed">
          Your conversations are currently stored only in this browser. Enable
          server-side saving to access them from any device and preserve them
          between sessions. You can disable this at any time.
        </p>
        <div className="flex gap-2 mt-2.5">
          <button
            onClick={onAccept}
            className="rounded-lg bg-[#986c43] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#845a38] transition-colors"
          >
            Enable saving
          </button>
          <button
            onClick={onDismiss}
            className="rounded-lg border border-[#d1c4b0] px-3 py-1.5 text-xs font-medium text-[#6d5841] hover:bg-[#f3ece2] transition-colors"
          >
            Not now
          </button>
        </div>
      </div>
      <button
        onClick={onDismiss}
        className="text-[#a99580] hover:text-[#6d5841]"
      >
        <X size={16} />
      </button>
    </div>
  );
}
