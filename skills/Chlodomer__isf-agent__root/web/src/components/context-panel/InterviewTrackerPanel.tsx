"use client";

import { Check, Minus, ArrowRight } from "lucide-react";
import { useProposalStore } from "@/lib/store";
import { INTERVIEW_SECTIONS, TOTAL_INTERVIEW_QUESTIONS } from "@/lib/types";
import { deriveInterviewAnsweredCount } from "@/lib/workflow-sync";

export default function InterviewTrackerPanel() {
  const interview = useProposalStore((s) => s.interview);
  const totalAnswered = deriveInterviewAnsweredCount(interview);

  const hasStarted = interview.currentSection !== null || interview.completedSections.length > 0;

  if (!hasStarted) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center h-64">
        <p className="text-sm text-gray-500 leading-relaxed">
          The interview will gather information about your research project
          across 4 sections: eligibility, research core, resources, and track
          record. This helps draft accurate, personalized proposal sections.
        </p>
      </div>
    );
  }

  const skippedCount = interview.skippedQuestions.length;

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-3 border-b border-gray-100">
        <h3 className="text-xs font-semibold text-gray-700 uppercase">
          Interview Progress
        </h3>
        <p className="mt-1 text-xs text-gray-500">
          {totalAnswered}/{TOTAL_INTERVIEW_QUESTIONS} questions answered
        </p>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {INTERVIEW_SECTIONS.map((section) => {
          const isCompleted = interview.completedSections.includes(section.id);
          const isCurrent = interview.currentSection === section.id;
          const currentQ = isCurrent ? (interview.currentQuestion ?? 0) : 0;
          const answeredCount = isCompleted
            ? section.totalQuestions
            : isCurrent
            ? currentQ - 1
            : 0;
          const progress =
            section.totalQuestions > 0
              ? (answeredCount / section.totalQuestions) * 100
              : 0;

          const skippedInSection = interview.skippedQuestions.filter(
            (sq) => sq.section === section.id
          );

          return (
            <div key={section.id}>
              <div className="flex items-center justify-between mb-1.5">
                <span
                  className={`text-sm ${
                    isCurrent
                      ? "font-medium text-teal-700"
                      : isCompleted
                      ? "text-gray-500"
                      : "text-gray-400"
                  }`}
                >
                  {section.label}
                </span>
                <span className="text-xs text-gray-400">
                  {answeredCount}/{section.totalQuestions}
                  {isCompleted && " done"}
                </span>
              </div>

              <div className="w-full h-1.5 bg-gray-100 rounded-full overflow-hidden mb-2">
                <div
                  className={`h-full rounded-full transition-all ${
                    isCompleted ? "bg-teal-500" : "bg-teal-400"
                  }`}
                  style={{ width: `${progress}%` }}
                />
              </div>

              {isCurrent && (
                <div className="space-y-1 ml-1">
                  {Array.from({ length: section.totalQuestions }, (_, i) => {
                    const qNum = i + 1;
                    const isAnswered = qNum < currentQ;
                    const isCurrentQ = qNum === currentQ;
                    const isSkipped = skippedInSection.some(
                      (sq) => sq.question === qNum
                    );

                    return (
                      <div
                        key={qNum}
                        className="flex items-center gap-2 text-xs"
                      >
                        {isAnswered ? (
                          <Check size={10} className="text-teal-500" />
                        ) : isCurrentQ ? (
                          <ArrowRight size={10} className="text-teal-600" />
                        ) : isSkipped ? (
                          <span className="w-2.5 h-2.5 rounded-full bg-amber-300" />
                        ) : (
                          <Minus size={10} className="text-gray-300" />
                        )}
                        <span
                          className={
                            isCurrentQ
                              ? "text-teal-700 font-medium"
                              : isAnswered
                              ? "text-gray-500"
                              : isSkipped
                              ? "text-amber-600"
                              : "text-gray-400"
                          }
                        >
                          Question {qNum}
                          {isSkipped && " (skipped)"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {skippedCount > 0 && (
        <div className="px-4 py-3 border-t border-gray-100">
          <p className="text-xs text-amber-600">
            {skippedCount} question{skippedCount > 1 ? "s" : ""} skipped — click
            to return
          </p>
        </div>
      )}
    </div>
  );
}
