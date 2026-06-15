"use client";

import { Check, Minus } from "lucide-react";
import { useProposalStore } from "@/lib/store";
import {
  INTERVIEW_SECTIONS,
  SECTION_ORDER,
  SECTION_LABELS,
  type Phase,
} from "@/lib/types";

interface SubProgressProps {
  phase: Phase;
}

function InterviewSubProgress() {
  const interview = useProposalStore((s) => s.interview);

  return (
    <>
      {INTERVIEW_SECTIONS.map((section) => {
        const isCompleted = interview.completedSections.includes(section.id);
        const isCurrent = interview.currentSection === section.id;
        const answeredInSection = isCurrent && interview.currentQuestion
          ? interview.currentQuestion - 1
          : isCompleted
          ? section.totalQuestions
          : 0;

        return (
          <div key={section.id} className="flex items-center gap-2 py-0.5">
            <div className="flex-shrink-0">
              {isCompleted ? (
                <Check size={12} className="text-teal-600" />
              ) : isCurrent ? (
                <div className="w-3 h-3 rounded-full border-2 border-teal-500 bg-teal-100" />
              ) : (
                <Minus size={12} className="text-gray-300" />
              )}
            </div>
            <span
              className={`text-xs ${
                isCurrent
                  ? "text-teal-700 font-medium"
                  : isCompleted
                  ? "text-gray-500"
                  : "text-gray-400"
              }`}
            >
              {section.label}
            </span>
            <span className="text-xs text-gray-400 ml-auto">
              {isCompleted
                ? `${section.totalQuestions}/${section.totalQuestions}`
                : isCurrent
                ? `${answeredInSection}/${section.totalQuestions}`
                : `0/${section.totalQuestions}`}
            </span>
          </div>
        );
      })}
    </>
  );
}

function DraftSubProgress() {
  const sections = useProposalStore((s) => s.proposalSections);

  return (
    <>
      {SECTION_ORDER.map((key) => {
        const section = sections[key];
        const isApproved = section.approved;
        const hasDraft = section.draft !== null;

        return (
          <div key={key} className="flex items-center gap-2 py-0.5">
            <div className="flex-shrink-0">
              {isApproved ? (
                <Check size={12} className="text-emerald-600" />
              ) : hasDraft ? (
                <div className="w-3 h-3 rounded-full border-2 border-blue-500 bg-blue-100" />
              ) : (
                <Minus size={12} className="text-gray-300" />
              )}
            </div>
            <span
              className={`text-xs ${
                isApproved
                  ? "text-emerald-600"
                  : hasDraft
                  ? "text-blue-600 font-medium"
                  : "text-gray-400"
              }`}
            >
              {SECTION_LABELS[key]}
            </span>
            <span className="text-xs text-gray-400 ml-auto">
              {isApproved ? "Approved" : hasDraft ? "Draft" : "--"}
            </span>
          </div>
        );
      })}
    </>
  );
}

export default function SubProgress({ phase }: SubProgressProps) {
  if (phase === 4) return <InterviewSubProgress />;
  if (phase === 5) return <DraftSubProgress />;
  return null;
}
