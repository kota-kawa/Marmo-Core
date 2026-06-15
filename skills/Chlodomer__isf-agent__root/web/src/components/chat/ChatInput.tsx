"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { Paperclip, ArrowUp } from "lucide-react";

interface ChatInputProps {
  onSend: (message: string) => void;
  onFileUpload?: (files: FileList) => void;
  disabled?: boolean;
}

export default function ChatInput({ onSend, onFileUpload, disabled }: ChatInputProps) {
  const [value, setValue] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!disabled) {
      textareaRef.current?.focus();
    }
  }, [disabled]);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [value, disabled, onSend]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 144) + "px"; // max 6 lines ~144px
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files.length > 0 && onFileUpload) {
      onFileUpload(e.dataTransfer.files);
    }
  };

  return (
    <div
      className="relative border-t border-[#dccdb9] bg-gradient-to-r from-white via-[#faf4ec] to-[#f3ece2]"
      onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
      onDragLeave={() => setIsDragOver(false)}
      onDrop={handleDrop}
    >
      {isDragOver && (
        <div className="absolute inset-0 z-10 m-1 flex items-center justify-center rounded-lg border-2 border-dashed border-[#c9ae90] bg-[#fff2e0]/90">
          <p className="text-base font-medium text-[#7a5738]">
            Drop your proposal, CV, or review file here
          </p>
        </div>
      )}

      <div className="flex items-end gap-2 p-3">
        <button
          onClick={() => fileInputRef.current?.click()}
          className="flex-shrink-0 rounded-lg p-2.5 text-[#8e7a65] transition-colors hover:bg-[#f3e9db] hover:text-[#665241]"
          aria-label="Attach file"
        >
          <Paperclip size={20} />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          className="hidden"
          multiple
          accept=".pdf,.doc,.docx,.txt,.md"
          onChange={(e) => e.target.files && onFileUpload?.(e.target.files)}
        />

        <textarea
          ref={textareaRef}
          autoFocus
          value={value}
          onChange={handleInput}
          onKeyDown={handleKeyDown}
          placeholder="Ask in plain language (for example: Help me improve this section)..."
          disabled={disabled}
          rows={1}
          className="flex-1 resize-none rounded-lg border border-[#d8c9b6] bg-[#fdf8f1] px-4 py-3 text-base focus:border-[#ab7e52] focus:outline-none focus:ring-2 focus:ring-[#d6b695]/50 disabled:opacity-50"
        />

        <button
          onClick={handleSubmit}
          disabled={!value.trim() || disabled}
          className="flex-shrink-0 rounded-lg bg-[#986c43] p-2.5 text-white transition-colors hover:bg-[#845a38] disabled:cursor-not-allowed disabled:opacity-30"
          aria-label="Send message"
        >
          <ArrowUp size={20} />
        </button>
      </div>

      <div className="px-4 pb-3 text-sm text-[#756451]">
        No special commands required. Just describe what you need.
      </div>
    </div>
  );
}
