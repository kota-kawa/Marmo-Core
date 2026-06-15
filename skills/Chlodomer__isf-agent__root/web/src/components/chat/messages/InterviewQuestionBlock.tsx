"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { INTERVIEW_SECTIONS } from "@/lib/types";

interface InterviewQuestionBlockProps {
  section: number;
  questionNum: number;
  totalInSection: number;
  question: string;
  guidance?: string;
  example?: string;
  onAction?: (action: string) => void;
}

export default function InterviewQuestionBlock({
  section,
  questionNum,
  totalInSection,
  question,
  guidance,
  example,
  onAction,
}: InterviewQuestionBlockProps) {
  const [exampleOpen, setExampleOpen] = useState(false);
  const sectionInfo = INTERVIEW_SECTIONS.find((s) => s.id === section);
  const sectionLabel = sectionInfo?.label ?? `Section ${section}`;

  return (
    <div className="my-3 bg-white rounded-lg border border-gray-200 border-l-4 border-l-teal-500 shadow-sm">
      <div className="p-4">
        <div className="mb-3">
          <span className="text-xs font-semibold uppercase tracking-wide text-teal-700">
            Interview: {sectionLabel} (Question {questionNum} of {totalInSection})
          </span>
        </div>

        <p className="text-base font-medium text-gray-800 leading-relaxed mb-2">
          {question}
        </p>

        {guidance && (
          <p className="text-sm text-gray-500 mt-2 leading-relaxed">{guidance}</p>
        )}

        {example && (
          <div className="mt-3">
            <button
              onClick={() => setExampleOpen(!exampleOpen)}
              className="flex items-center gap-1 text-sm text-teal-600 hover:text-teal-700 transition-colors"
            >
              {exampleOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              {exampleOpen ? "Hide example" : "Show example"}
            </button>
            {exampleOpen && (
              <div className="mt-2 p-3 bg-teal-50 rounded-md text-sm text-teal-800 italic">
                {example}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="flex gap-2 px-4 py-3 border-t border-gray-100 bg-gray-50/50 rounded-b-lg">
        <button
          onClick={() => onAction?.("skip")}
          className="text-sm px-3 py-1.5 rounded-md border border-gray-200 bg-white text-gray-500 hover:bg-gray-50 transition-colors"
        >
          Skip
        </button>
        <button
          onClick={() => onAction?.("back")}
          className="text-sm px-3 py-1.5 rounded-md border border-gray-200 bg-white text-gray-500 hover:bg-gray-50 transition-colors"
        >
          Back to previous
        </button>
        <button
          onClick={() => onAction?.("why")}
          className="text-sm px-3 py-1.5 rounded-md border border-teal-200 bg-teal-50 text-teal-700 hover:bg-teal-100 transition-colors"
        >
          Why does this matter?
        </button>
      </div>
    </div>
  );
}
