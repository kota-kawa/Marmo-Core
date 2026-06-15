"use client";

import { useCallback, useState } from "react";
import { Database, Trash2, X } from "lucide-react";

interface ChatSettingsModalProps {
  consent: boolean | null;
  onUpdateConsent: (consent: boolean) => Promise<boolean>;
  onClose: () => void;
}

export default function ChatSettingsModal({
  consent,
  onUpdateConsent,
  onClose,
}: ChatSettingsModalProps) {
  const [isPurging, setIsPurging] = useState(false);
  const [isToggling, setIsToggling] = useState(false);
  const [purgeResult, setPurgeResult] = useState<string | null>(null);

  const handleToggle = useCallback(async () => {
    setIsToggling(true);
    const newValue = !consent;
    await onUpdateConsent(newValue);
    setIsToggling(false);
  }, [consent, onUpdateConsent]);

  const handlePurge = useCallback(async () => {
    if (!confirm("Delete all server-side chat history? Your local data will remain.")) {
      return;
    }
    setIsPurging(true);
    try {
      const res = await fetch("/api/threads/purge", { method: "DELETE" });
      if (res.ok) {
        const data = await res.json();
        setPurgeResult(`Deleted ${data.deleted} thread(s) from the server.`);
      } else {
        setPurgeResult("Failed to purge server data.");
      }
    } catch {
      setPurgeResult("Failed to purge server data.");
    } finally {
      setIsPurging(false);
    }
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-[#d1c4b0] bg-[#fdf8f1] shadow-2xl">
        <div className="flex items-center justify-between border-b border-[#e5ddd0] px-5 py-4">
          <h2 className="text-base font-semibold text-[#2f2924]">
            Chat Settings
          </h2>
          <button
            onClick={onClose}
            className="text-[#a99580] hover:text-[#6d5841]"
          >
            <X size={18} />
          </button>
        </div>

        <div className="px-5 py-4 space-y-4">
          {/* Persistence toggle */}
          <div className="flex items-start gap-3">
            <Database size={18} className="text-[#8b6e50] mt-0.5" />
            <div className="flex-1">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold text-[#3f342b]">
                  Save chat history
                </p>
                <button
                  onClick={handleToggle}
                  disabled={isToggling || consent === null}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    consent
                      ? "bg-[#986c43]"
                      : "bg-[#c4b5a2]"
                  } ${isToggling ? "opacity-50" : ""}`}
                >
                  <span
                    className={`inline-block h-4 w-4 rounded-full bg-white transition-transform ${
                      consent ? "translate-x-6" : "translate-x-1"
                    }`}
                  />
                </button>
              </div>
              <p className="text-xs text-[#6d5841] mt-1 leading-relaxed">
                {consent
                  ? "Conversations are saved to your account. Disable to stop saving (existing data remains until purged)."
                  : "Conversations are only stored in this browser. Enable to save them to your account."}
              </p>
            </div>
          </div>

          {/* Purge section */}
          {consent !== null && (
            <div className="flex items-start gap-3 pt-2 border-t border-[#e5ddd0]">
              <Trash2 size={18} className="text-[#a5674a] mt-0.5" />
              <div className="flex-1">
                <p className="text-sm font-semibold text-[#3f342b]">
                  Delete server data
                </p>
                <p className="text-xs text-[#6d5841] mt-1 leading-relaxed">
                  Permanently remove all chat history stored on the server. Your
                  local browser data is not affected.
                </p>
                {purgeResult && (
                  <p className="text-xs text-[#6d5841] mt-1 font-medium">
                    {purgeResult}
                  </p>
                )}
                <button
                  onClick={handlePurge}
                  disabled={isPurging}
                  className="mt-2 rounded-lg border border-[#d4a597] px-3 py-1.5 text-xs font-medium text-[#a5674a] hover:bg-[#fdf0ec] transition-colors disabled:opacity-50"
                >
                  {isPurging ? "Deleting..." : "Delete all server data"}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="border-t border-[#e5ddd0] px-5 py-3 flex justify-end">
          <button
            onClick={onClose}
            className="rounded-lg bg-[#312a24] px-4 py-1.5 text-xs font-semibold text-white hover:bg-[#241f1b] transition-colors"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
