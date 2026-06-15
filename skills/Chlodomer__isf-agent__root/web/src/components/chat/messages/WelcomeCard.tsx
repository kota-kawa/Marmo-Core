"use client";

import { Sparkles, Upload, Clock, Compass } from "lucide-react";
import { useProposalStore } from "@/lib/store";

interface WelcomeCardProps {
  onAction?: (action: string) => void;
}

export default function WelcomeCard({ onAction }: WelcomeCardProps) {
  const name = useProposalStore((s) => s.researcherInfo.name);
  const greeting = name?.trim() ? `Welcome, ${name.trim()}` : "Welcome";

  return (
    <div className="mt-3 mb-2 rounded-lg border border-[#dac9b2] bg-gradient-to-br from-white via-[#fffaf4] to-[#f7efe3] shadow-[0_16px_34px_-30px_rgba(47,41,36,0.65)]">
      <div className="p-5">
        <h2 className="font-display text-2xl font-semibold text-[#2f2924] mb-2">
          {greeting} to Granite
        </h2>
        <p className="text-base text-[#665645] leading-relaxed mb-5">
          Granite helps you prepare a competitive proposal for the Israel Science
          Foundation Personal Research Grant. The process has 7 phases and
          typically takes a few sessions. We can save progress and resume
          anytime.
        </p>

        <div className="space-y-3">
          <button
            onClick={() => onAction?.("start-fresh")}
            className="w-full flex items-center gap-4 p-4 rounded-lg border-2 border-[#ddc4a6] bg-[#fff2e1] hover:bg-[#ffe8cf] transition-colors text-left"
          >
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-[#f4debf] flex items-center justify-center">
              <Sparkles size={20} className="text-[#94653f]" />
            </div>
            <div>
              <p className="text-base font-medium text-[#7a5332]">Start Fresh</p>
              <p className="text-base text-[#855f3d]">Begin a new proposal from scratch</p>
            </div>
          </button>

          <button
            onClick={() => onAction?.("upload-first")}
            className="w-full flex items-center gap-4 p-4 rounded-lg border-2 border-[#d5c2ab] bg-[#f9f1e7] hover:bg-[#f4e8d9] transition-colors text-left"
          >
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-[#ebdccb] flex items-center justify-center">
              <Upload size={20} className="text-[#6b5a49]" />
            </div>
            <div>
              <p className="text-base font-medium text-[#544637]">Upload Past Proposals First</p>
              <p className="text-base text-[#625345]">
                Share past proposals so I can learn from them
              </p>
            </div>
          </button>

          <button
            onClick={() => onAction?.("resume")}
            className="w-full flex items-center gap-4 p-4 rounded-lg border-2 border-[#ccd2d7] bg-[#eef2f5] hover:bg-[#e5ebf0] transition-colors text-left"
          >
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-[#dde4ea] flex items-center justify-center">
              <Clock size={20} className="text-[#50606f]" />
            </div>
            <div>
              <p className="text-base font-medium text-[#3f4d5b]">Resume Previous Session</p>
              <p className="text-base text-[#4a5a68]">Continue where you left off</p>
            </div>
          </button>

          <button
            onClick={() => onAction?.("onboarding")}
            className="w-full flex items-center gap-4 p-4 rounded-lg border-2 border-[#cfc6ba] bg-[#f5f1ec] hover:bg-[#efe8df] transition-colors text-left"
          >
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-[#e7ddd2] flex items-center justify-center">
              <Compass size={20} className="text-[#5e5348]" />
            </div>
            <div>
              <p className="text-base font-medium text-[#4f453b]">Repeat Onboarding</p>
              <p className="text-base text-[#5c5147]">Review the workflow in a simple guided tour</p>
            </div>
          </button>
        </div>

        <div className="mt-4 rounded-lg border border-[#d9c9b5] bg-[#fbf5ec] px-4 py-3">
          <p className="text-sm font-semibold uppercase tracking-wide text-[#735d46] mb-2">You Can Type Naturally</p>
          <p className="text-base text-[#5e5042] leading-relaxed">
            No special command syntax is required. Try plain requests like:
          </p>
          <div className="mt-2 flex flex-wrap gap-2">
            <span className="rounded-full border border-[#d4c2ab] bg-white px-3 py-1 text-sm text-[#5f5041]">
              &quot;Help me draft a stronger abstract&quot;
            </span>
            <span className="rounded-full border border-[#d4c2ab] bg-white px-3 py-1 text-sm text-[#5f5041]">
              &quot;Check if I&apos;m missing compliance items&quot;
            </span>
            <span className="rounded-full border border-[#d4c2ab] bg-white px-3 py-1 text-sm text-[#5f5041]">
              &quot;What should I do next?&quot;
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
