import { describe, expect, it } from "vitest";
import type { InterviewState, ProposalSections } from "./types";
import {
  advanceInterviewAfterUserResponse,
  buildCompiledProposalPreview,
  deriveInterviewAnsweredCount,
  derivePhaseFromMilestones,
  extractSectionDraftsFromAssistantReply,
  getNextApprovableSection,
} from "./workflow-sync";

describe("workflow-sync", () => {
  it("extracts section drafts from headed assistant output", () => {
    const reply = `
Abstract
This abstract is intentionally long enough to cross the extraction threshold with clear intent, realistic grant framing, a defined research gap, and expected contribution over multiple phases. It also names primary sources, key methods, and measurable outcomes to emulate the density of a real grant abstract section.

Specific Aims
Aim one evaluates archival exchange mechanisms and aim two compares institutional mediation. Each aim includes methods, expected outputs, contingency routes, and measurable milestones over the project period. The section states what success looks like and how evidence will be validated.
`;

    const drafts = extractSectionDraftsFromAssistantReply(reply, "please draft abstract and aims");
    expect(drafts.map((draft) => draft.section)).toEqual(["abstract", "aims"]);
    expect(drafts[0]?.wordCount).toBeGreaterThan(20);
  });

  it("advances interview progress after each user response", () => {
    const start: InterviewState = {
      currentSection: null,
      currentQuestion: null,
      completedSections: [],
      skippedQuestions: [],
    };

    const afterFirst = advanceInterviewAfterUserResponse(start);
    expect(afterFirst.currentSection).toBe(1);
    expect(afterFirst.currentQuestion).toBe(2);
    expect(deriveInterviewAnsweredCount(afterFirst)).toBe(1);
  });

  it("derives phase from milestones", () => {
    expect(
      derivePhaseFromMilestones({
        requirementsFetched: false,
        learningsCount: 0,
        interviewAnswered: 0,
        draftedCount: 0,
        validationRun: false,
        readyForSubmission: false,
      })
    ).toBe(1);

    expect(
      derivePhaseFromMilestones({
        requirementsFetched: true,
        learningsCount: 1,
        interviewAnswered: 10,
        draftedCount: 2,
        validationRun: true,
        readyForSubmission: false,
      })
    ).toBe(6);
  });

  it("builds compiled preview and finds next approvable section", () => {
    const sections: ProposalSections = {
      abstract: {
        draft: "Abstract text with enough words to be visible in preview.",
        approved: false,
        wordCount: 10,
        charCount: 55,
        pageCount: 1,
      },
      background: { draft: null, approved: false, wordCount: null, charCount: null, pageCount: null },
      aims: { draft: "Aims text", approved: false, wordCount: 2, charCount: 9, pageCount: 1 },
      methods: { draft: null, approved: false, wordCount: null, charCount: null, pageCount: null },
      innovation: { draft: null, approved: false, wordCount: null, charCount: null, pageCount: null },
      budget: { draft: null, approved: false, wordCount: null, charCount: null, pageCount: null },
      risks: { draft: null, approved: false, wordCount: null, charCount: null, pageCount: null },
      bibliography: { entries: [] },
    };

    const preview = buildCompiledProposalPreview(sections);
    expect(preview).toContain("Abstract");
    expect(preview).toContain("Specific Aims");
    expect(getNextApprovableSection(sections)).toBe("abstract");
  });
});
