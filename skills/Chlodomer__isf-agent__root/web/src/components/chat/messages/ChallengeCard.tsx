"use client";

import type { ChallengeIntensity } from "@/lib/types";

interface ChallengeCardProps {
  category: string;
  intensity: ChallengeIntensity;
  question: string;
  context: string;
  onAction?: (action: string) => void;
}

function IntensityDots({ level }: { level: ChallengeIntensity }) {
  return (
    <div className="flex gap-1">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className={`w-2 h-2 rounded-full ${
            i <= level ? "bg-amber-500" : "bg-gray-300"
          }`}
        />
      ))}
    </div>
  );
}

export default function ChallengeCard({
  category,
  intensity,
  question,
  context,
  onAction,
}: ChallengeCardProps) {
  return (
    <div className="my-3 bg-white rounded-lg border border-gray-200 border-l-4 border-l-amber-500 shadow-sm">
      <div className="p-4">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold uppercase tracking-wide text-amber-700">
            Challenge: {category}
          </span>
          <IntensityDots level={intensity} />
        </div>

        <p className="text-gray-700 italic leading-relaxed mb-3">
          &ldquo;{question}&rdquo;
        </p>

        <p className="text-sm text-gray-500">
          <span className="font-medium">Why this matters:</span> {context}
        </p>
      </div>

      <div className="flex gap-2 px-4 py-3 border-t border-gray-100 bg-gray-50/50 rounded-b-lg">
        <button
          onClick={() => onAction?.("answer")}
          className="text-sm px-3 py-1.5 rounded-md border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Answer in chat
        </button>
        <button
          onClick={() => onAction?.("skip")}
          className="text-sm px-3 py-1.5 rounded-md border border-gray-200 bg-white text-gray-500 hover:bg-gray-50 transition-colors"
        >
          Skip for now
        </button>
        <button
          onClick={() => onAction?.("harder")}
          className="text-sm px-3 py-1.5 rounded-md border border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 transition-colors"
        >
          Harder question
        </button>
      </div>
    </div>
  );
}
