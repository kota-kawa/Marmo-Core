"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Image from "next/image";
import { ArrowLeft, ArrowRight, CheckCircle2 } from "lucide-react";

export interface OnboardingProfile {
  name: string;
  affiliation: string;
}

interface OnboardingExperienceProps {
  onComplete: (profile: OnboardingProfile) => void;
}

interface OnboardingStep {
  id: number;
  title: string;
  summary: string;
  points: string[];
  examples?: string[];
}

const STEPS: OnboardingStep[] = [
  {
    id: 1,
    title: "Welcome to Granite",
    summary: "This onboarding takes about two minutes and sets up your personalized workspace.",
    points: [
      "You will move through a short guided flow.",
      "First, type your name so the assistant can address you personally.",
      "The workflow now includes source grounding, compliance checks, and readiness tracking.",
      "You can go back at any time during onboarding.",
    ],
  },
  {
    id: 2,
    title: "Tell Us Your Affiliation",
    summary: "Share your departmental affiliation so guidance can be contextualized.",
    points: [
      "Example: Department of Physics, Tel Aviv University.",
      "This helps tailor recommendations and examples.",
      "You can update this later if needed.",
    ],
  },
  {
    id: 3,
    title: "How To Interact (No Technical Syntax Needed)",
    summary: "Write naturally, like you are speaking to a colleague. You do not need slash commands.",
    points: [
      "Type full questions or requests in plain language.",
      "Press Enter to send. Use Shift+Enter for a new line.",
      "Use the clickable suggestion buttons if you prefer not to type.",
      "Commands exist as optional shortcuts only, and you can ignore them.",
    ],
    examples: [
      "Help me draft a clearer Specific Aims section.",
      "What information is still missing before we can submit?",
      "Please review this paragraph for reviewer clarity.",
    ],
  },
  {
    id: 4,
    title: "Ground Drafts In Your Own Materials",
    summary: "Attach source files so the assistant can stay anchored to your evidence.",
    points: [
      "Use the paperclip in chat to upload papers, past proposals, and reviewer notes.",
      "The assistant keeps track of uploaded sources automatically.",
      "When needed, responses can reference source IDs like [S1] so evidence is traceable.",
      "Upload early so drafting stays grounded from the beginning.",
    ],
  },
  {
    id: 5,
    title: "Compliance And Readiness",
    summary: "The assistant now surfaces blockers early so submission feels predictable.",
    points: [
      "Run compliance checks during drafting, not only at the end.",
      "Fix actions in chat and the Compliance panel guide what to do next.",
      "The Readiness view summarizes blockers, progress, and next actions in one place.",
      "Use this as your pre-submission control center.",
    ],
  },
  {
    id: 6,
    title: "What You Will See In The Workspace",
    summary: "The center panel is your conversation, with operational context around it.",
    points: [
      "Main chat is optimized for iterative drafting and revision.",
      "Side panels expose operations, readiness, draft, compliance, and learnings.",
      "Quick Actions include direct access to submission readiness.",
      "You can replay onboarding from the welcome card whenever needed.",
    ],
  },
  {
    id: 7,
    title: "You Are Ready",
    summary: "After this step, you will enter the working screen.",
    points: [
      "Start by describing your project in 3-5 sentences.",
      "Upload source files early so generated drafts stay grounded.",
      "Run compliance and readiness checks before major revisions.",
      "Move at your own pace. You can resume and continue anytime.",
    ],
  },
];

export default function OnboardingExperience({ onComplete }: OnboardingExperienceProps) {
  const [index, setIndex] = useState(0);
  const [name, setName] = useState("");
  const [affiliation, setAffiliation] = useState("");

  const step = STEPS[index];
  const isFirst = index === 0;
  const isAffiliationStep = index === 1;
  const isLast = index === STEPS.length - 1;
  const hasName = name.trim().length >= 2;
  const hasAffiliation = affiliation.trim().length >= 2;
  const gateSatisfied = isFirst ? hasName : isAffiliationStep ? hasAffiliation : true;
  const progress = useMemo(
    () => Math.round(((index + 1) / STEPS.length) * 100),
    [index]
  );

  const moveNext = useCallback(() => {
    if (!gateSatisfied) return;

    if (isLast) {
      onComplete({
        name: name.trim(),
        affiliation: affiliation.trim(),
      });
      return;
    }

    setIndex((current) => current + 1);
  }, [affiliation, gateSatisfied, isLast, name, onComplete]);

  const moveBack = useCallback(() => {
    if (isFirst) return;
    setIndex((current) => current - 1);
  }, [isFirst]);

  useEffect(() => {
    const handleEnter = (event: KeyboardEvent) => {
      if (
        event.key !== "Enter" ||
        event.shiftKey ||
        event.metaKey ||
        event.ctrlKey ||
        event.altKey ||
        event.repeat
      ) {
        return;
      }

      const target = event.target as HTMLElement | null;
      if (target?.tagName === "TEXTAREA" || target?.isContentEditable) {
        return;
      }

      event.preventDefault();
      moveNext();
    };

    window.addEventListener("keydown", handleEnter);
    return () => window.removeEventListener("keydown", handleEnter);
  }, [moveNext]);

  return (
    <div className="min-h-screen w-full bg-[radial-gradient(circle_at_14%_10%,rgba(188,159,118,0.20),transparent_42%),radial-gradient(circle_at_84%_12%,rgba(99,134,128,0.15),transparent_40%),linear-gradient(180deg,#f8f4ee_0%,#efe9df_100%)] px-4 py-6 sm:px-8 sm:py-8">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-5 rounded-3xl border border-[#ddcdb8] bg-white/92 p-6 shadow-[0_30px_70px_-45px_rgba(58,44,27,0.55)] backdrop-blur-sm sm:p-8">
        <div className="flex items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-xl border border-[#d9ccba] bg-[#f4ece1]">
            <Image
              src="/granite-logo.png"
              alt="Granite logo"
              width={40}
              height={40}
              className="h-10 w-10 rounded-lg object-cover"
            />
          </div>
          <div>
            <p className="text-sm font-semibold uppercase tracking-[0.14em] text-[#876c4f]">
              Guided Onboarding
            </p>
            <p className="text-base text-slate-600">
              Step {index + 1} of {STEPS.length}
            </p>
          </div>
        </div>

        <div className="h-2.5 w-full overflow-hidden rounded-full bg-[#eadfce]">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[#b88756] via-[#c79a6e] to-[#8ca89e] transition-all"
            style={{ width: `${Math.max(progress, 8)}%` }}
          />
        </div>

        <div className="rounded-2xl border border-[#e6d8c3] bg-[#fffaf3] p-6">
          <h1 className="text-3xl font-semibold text-[#3e2f1d]">{step.title}</h1>
          <p className="mt-2 text-lg leading-relaxed text-[#66564a]">{step.summary}</p>

          <ul className="mt-4 space-y-3">
            {step.points.map((point) => (
              <li key={point} className="flex items-start gap-2.5 text-base leading-relaxed text-[#4f4338]">
                <CheckCircle2 size={18} className="mt-1 flex-shrink-0 text-[#a98359]" />
                <span>{point}</span>
              </li>
            ))}
          </ul>

          {step.examples && step.examples.length > 0 && (
            <div className="mt-5 rounded-xl border border-[#e4d7c4] bg-white/90 p-4">
              <p className="text-sm font-semibold uppercase tracking-[0.1em] text-[#8a6f50]">
                Try Asking Like This
              </p>
              <div className="mt-3 flex flex-wrap gap-2">
                {step.examples.map((example) => (
                  <span
                    key={example}
                    className="rounded-full border border-[#dac9b2] bg-[#fff8ee] px-3 py-1.5 text-sm text-[#654f38]"
                  >
                    {example}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-[#e2d3bd] bg-[#faf4ea] p-5">
          {isFirst ? (
            <>
              <p className="text-base font-medium text-[#6b543c]">
                Type your name, then press Continue.
              </p>
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                onKeyDown={(e) => {
                  if (e.key !== "Enter" || !gateSatisfied) return;
                  e.preventDefault();
                  e.stopPropagation();
                  moveNext();
                }}
                placeholder="Your name"
                className="mt-3 w-full rounded-lg border border-[#d9c8b0] bg-white px-4 py-3 text-base text-[#3f3223] outline-none transition-colors focus:border-[#be9f7f] focus:ring-2 focus:ring-[#d8bf9e]/40"
                autoFocus
              />
            </>
          ) : isAffiliationStep ? (
            <>
              <p className="text-base font-medium text-[#6b543c]">
                Share your department or affiliation, then press Continue.
              </p>
              <input
                value={affiliation}
                onChange={(event) => setAffiliation(event.target.value)}
                onKeyDown={(e) => {
                  if (e.key !== "Enter" || !gateSatisfied) return;
                  e.preventDefault();
                  e.stopPropagation();
                  moveNext();
                }}
                placeholder="Department / Affiliation"
                className="mt-3 w-full rounded-lg border border-[#d9c8b0] bg-white px-4 py-3 text-base text-[#3f3223] outline-none transition-colors focus:border-[#be9f7f] focus:ring-2 focus:ring-[#d8bf9e]/40"
                autoFocus
              />
            </>
          ) : (
            <>
              <p className="text-base font-medium text-[#6b543c]">
                Press {isLast ? "Enter Workspace" : "Continue"} to proceed.
              </p>
            </>
          )}
        </div>

        <div className="flex items-center justify-between gap-3">
          <button
            onClick={moveBack}
            disabled={isFirst}
            className="inline-flex items-center gap-1.5 rounded-lg border border-[#d6c5ad] bg-white px-4 py-2.5 text-base font-medium text-[#6e5840] transition-colors hover:bg-[#f7efe5] disabled:cursor-not-allowed disabled:opacity-40"
          >
            <ArrowLeft size={14} />
            Back
          </button>

          <button
            onClick={moveNext}
            disabled={!gateSatisfied}
            className="inline-flex items-center gap-1.5 rounded-lg bg-[#9f734a] px-5 py-2.5 text-base font-semibold text-white transition-colors hover:bg-[#8e6641] disabled:cursor-not-allowed disabled:opacity-35"
          >
            {isLast ? "Enter Workspace" : "Continue"}
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
}
