import {
  INTERVIEW_SECTIONS,
  SECTION_LABELS,
  SECTION_ORDER,
  TOTAL_INTERVIEW_QUESTIONS,
  type ContextTab,
  type InterviewState,
  type Phase,
  type ProposalSections,
  type SectionName,
} from "./types";

export interface DraftExtraction {
  section: SectionName;
  draft: string;
  wordCount: number;
  charCount: number;
  pageCount: number;
}

type LimitTone = "ok" | "near" | "over";

export interface SectionLimitInfo {
  limit: number | null;
  tone: LimitTone;
}

export const SECTION_SOFT_WORD_LIMITS: Record<SectionName, number | null> = {
  abstract: 300,
  background: 2200,
  aims: 900,
  methods: 3500,
  innovation: 700,
  budget: 800,
  risks: 900,
};

function normalizeText(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9\s]/g, " ").replace(/\s+/g, " ").trim();
}

function mapLabelToSection(rawLabel: string): SectionName | null {
  const label = normalizeText(rawLabel);
  if (!label) return null;
  if (label.includes("abstract")) return "abstract";
  if (label.includes("background") || label.includes("literature")) return "background";
  if (label.includes("specific aims") || label === "aims" || label.includes("objectives")) return "aims";
  if (
    label.includes("methodology") ||
    label.includes("methods") ||
    label.includes("research plan")
  ) {
    return "methods";
  }
  if (label.includes("innovation") || label.includes("significance")) return "innovation";
  if (label.includes("budget") || label.includes("justification")) return "budget";
  if (label.includes("risk") || label.includes("ethical") || label.includes("mitigation")) return "risks";
  return null;
}

function isLikelyHeading(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed) return false;
  if (trimmed.length > 80) return false;
  const cleaned = trimmed
    .replace(/^#{1,6}\s*/, "")
    .replace(/^[0-9]+\.\s*/, "")
    .replace(/^[-*]\s*/, "")
    .trim();
  if (!cleaned) return false;
  if (cleaned.split(/\s+/).length > 9) return false;
  if (/[.!?]/.test(cleaned)) return false;
  return /[A-Za-z]/.test(cleaned);
}

export function countWords(value: string): number {
  return value.trim().split(/\s+/).filter(Boolean).length;
}

export function countCharacters(value: string): number {
  return value.trim().length;
}

export function estimatePagesFromWords(wordCount: number): number {
  if (wordCount <= 0) return 0;
  return Math.max(1, Math.round((wordCount / 350) * 10) / 10);
}

export function getSectionLimitInfo(section: SectionName, wordCount: number | null | undefined): SectionLimitInfo {
  const limit = SECTION_SOFT_WORD_LIMITS[section];
  if (!limit || !wordCount || wordCount <= 0) {
    return { limit, tone: "ok" };
  }
  if (wordCount > limit) return { limit, tone: "over" };
  if (wordCount >= Math.floor(limit * 0.9)) return { limit, tone: "near" };
  return { limit, tone: "ok" };
}

function shouldKeepSectionDraft(section: SectionName, text: string): boolean {
  const words = countWords(text);
  if (section === "abstract") return words >= 45;
  return words >= 35;
}

export function extractSectionDraftsFromAssistantReply(
  assistantText: string,
  userPrompt?: string
): DraftExtraction[] {
  const trimmed = assistantText.trim();
  if (!trimmed) return [];

  const results = new Map<SectionName, DraftExtraction>();
  const lines = trimmed.split("\n");
  let activeSection: SectionName | null = null;
  let activeLines: string[] = [];

  const flushActive = () => {
    if (!activeSection) return;
    const draft = activeLines.join("\n").trim();
    if (!draft || !shouldKeepSectionDraft(activeSection, draft)) {
      activeSection = null;
      activeLines = [];
      return;
    }
    const wordCount = countWords(draft);
    results.set(activeSection, {
      section: activeSection,
      draft,
      wordCount,
      charCount: countCharacters(draft),
      pageCount: estimatePagesFromWords(wordCount),
    });
    activeSection = null;
    activeLines = [];
  };

  for (const line of lines) {
    const inlineMatch = line.match(
      /^#{0,6}\s*([A-Za-z][A-Za-z0-9\s&/()\-]{1,80})\s*:\s*(.+)$/
    );
    if (inlineMatch) {
      const section = mapLabelToSection(inlineMatch[1]);
      if (section) {
        flushActive();
        activeSection = section;
        activeLines = [inlineMatch[2]];
        continue;
      }
    }

    if (isLikelyHeading(line)) {
      const headingSection = mapLabelToSection(line);
      if (headingSection) {
        flushActive();
        activeSection = headingSection;
        activeLines = [];
        continue;
      }
    }

    if (activeSection) {
      activeLines.push(line);
    }
  }
  flushActive();

  if (results.size === 0 && userPrompt) {
    const requestedSection = mapLabelToSection(userPrompt);
    if (requestedSection && shouldKeepSectionDraft(requestedSection, trimmed)) {
      const wordCount = countWords(trimmed);
      results.set(requestedSection, {
        section: requestedSection,
        draft: trimmed,
        wordCount,
        charCount: countCharacters(trimmed),
        pageCount: estimatePagesFromWords(wordCount),
      });
    }
  }

  return SECTION_ORDER.map((section) => results.get(section)).filter(
    (value): value is DraftExtraction => Boolean(value)
  );
}

export function deriveInterviewAnsweredCount(interview: InterviewState): number {
  const completed = INTERVIEW_SECTIONS.reduce((sum, section) => {
    return interview.completedSections.includes(section.id)
      ? sum + section.totalQuestions
      : sum;
  }, 0);

  if (!interview.currentSection || !interview.currentQuestion) {
    return Math.min(completed, TOTAL_INTERVIEW_QUESTIONS);
  }

  const currentSection = INTERVIEW_SECTIONS.find(
    (section) => section.id === interview.currentSection
  );
  if (!currentSection) return Math.min(completed, TOTAL_INTERVIEW_QUESTIONS);

  const inProgress = Math.max(interview.currentQuestion - 1, 0);
  return Math.min(completed + inProgress, TOTAL_INTERVIEW_QUESTIONS);
}

export function advanceInterviewAfterUserResponse(interview: InterviewState): InterviewState {
  if (!interview.currentSection || !interview.currentQuestion) {
    return {
      ...interview,
      currentSection: INTERVIEW_SECTIONS[0].id,
      currentQuestion: 2,
    };
  }

  const section = INTERVIEW_SECTIONS.find((item) => item.id === interview.currentSection);
  if (!section) return interview;

  const nextQuestion = interview.currentQuestion + 1;
  if (nextQuestion <= section.totalQuestions) {
    return {
      ...interview,
      currentQuestion: nextQuestion,
    };
  }

  const completedSections = interview.completedSections.includes(section.id)
    ? interview.completedSections
    : [...interview.completedSections, section.id];
  const nextSection = INTERVIEW_SECTIONS.find((item) => item.id === section.id + 1);

  if (!nextSection) {
    return {
      ...interview,
      currentSection: null,
      currentQuestion: null,
      completedSections: INTERVIEW_SECTIONS.map((item) => item.id),
    };
  }

  return {
    ...interview,
    completedSections,
    currentSection: nextSection.id,
    currentQuestion: 1,
  };
}

interface PhaseInput {
  requirementsFetched: boolean;
  learningsCount: number;
  interviewAnswered: number;
  draftedCount: number;
  validationRun: boolean;
  readyForSubmission: boolean;
}

export function derivePhaseFromMilestones(input: PhaseInput): Phase {
  if (input.readyForSubmission) return 7;
  if (input.validationRun) return 6;
  if (input.draftedCount > 0) return 5;
  if (input.interviewAnswered > 0) return 4;
  if (input.learningsCount > 0) return 3;
  if (input.requirementsFetched) return 2;
  return 1;
}

export function phaseToContextTab(phase: Phase): ContextTab {
  if (phase === 3) return "learnings";
  if (phase === 4) return "interview";
  if (phase === 5) return "draft";
  if (phase === 6) return "compliance";
  if (phase === 7) return "readiness";
  return "operations";
}

export function buildCompiledProposalPreview(sections: ProposalSections): string {
  const blocks = SECTION_ORDER.map((section) => {
    const draft = sections[section].draft?.trim();
    if (!draft) return null;
    return `${SECTION_LABELS[section]}\n\n${draft}`;
  }).filter((value): value is string => Boolean(value));

  return blocks.join("\n\n---\n\n");
}

export function getNextApprovableSection(sections: ProposalSections): SectionName | null {
  for (const section of SECTION_ORDER) {
    if (sections[section].draft && !sections[section].approved) {
      return section;
    }
  }
  return null;
}
