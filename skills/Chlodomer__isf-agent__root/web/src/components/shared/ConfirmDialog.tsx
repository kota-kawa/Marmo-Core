"use client";

import { useCallback, useEffect, useRef } from "react";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: "danger" | "default";
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  variant = "default",
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) cancelRef.current?.focus();
  }, [open]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") onCancel();
    },
    [onCancel]
  );

  if (!open) return null;

  const confirmButtonClass =
    variant === "danger"
      ? "rounded-lg border border-[#d4a597] bg-[#a5674a] px-4 py-1.5 text-xs font-semibold text-white hover:bg-[#8e5840] transition-colors"
      : "rounded-lg bg-[#312a24] px-4 py-1.5 text-xs font-semibold text-white hover:bg-[#241f1b] transition-colors";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm"
      onKeyDown={handleKeyDown}
    >
      <div className="w-full max-w-sm rounded-2xl border border-[#d1c4b0] bg-[#fdf8f1] shadow-2xl">
        <div className="px-5 py-4">
          <h3 className="text-sm font-semibold text-[#2f2924]">{title}</h3>
          <p className="mt-2 text-xs text-[#6d5841] leading-relaxed">
            {message}
          </p>
        </div>
        <div className="border-t border-[#e5ddd0] px-5 py-3 flex justify-end gap-2">
          <button
            ref={cancelRef}
            onClick={onCancel}
            className="rounded-lg border border-[#d1c4b0] px-4 py-1.5 text-xs font-semibold text-[#6d5841] hover:bg-[#f5ede3] transition-colors"
          >
            {cancelLabel}
          </button>
          <button onClick={onConfirm} className={confirmButtonClass}>
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
