import {
  SECTION_ORDER,
  type ProposalSections,
  type ReferenceSource,
  type ResearcherInfo,
  type ValidationState,
} from "./types";

export type ReadinessStatus = "ready" | "in_progress" | "blocked";

export interface ReadinessItem {
  id: string;
  title: string;
  detail: string;
  status: ReadinessStatus;
  action?: string;
}

export interface ReadinessSnapshot {
  score: number;
  blockers: number;
  inProgress: number;
  ready: boolean;
  items: ReadinessItem[];
}

interface ReadinessInput {
  researcherInfo: ResearcherInfo;
  proposalSections: ProposalSections;
  validation: ValidationState;
  referenceSources: ReferenceSource[];
}

function hasContent(value: string | null): boolean {
  return typeof value === "string" && value.trim().length > 0;
}

export function buildReadinessSnapshot(input: ReadinessInput): ReadinessSnapshot {
  const draftedCount = SECTION_ORDER.filter((sectionName) =>
    hasContent(input.proposalSections[sectionName].draft)
  ).length;
  const approvedCount = SECTION_ORDER.filter(
    (sectionName) => input.proposalSections[sectionName].approved
  ).length;
  const hasProfile = hasContent(input.researcherInfo.name) && hasContent(input.researcherInfo.department);

  const items: ReadinessItem[] = [
    {
      id: "profile",
      title: "Researcher profile context",
      detail: hasProfile
        ? "Name and affiliation are set for personalized drafting."
        : "Add name and affiliation in onboarding context.",
      status: hasProfile ? "ready" : "in_progress",
      action: "replay-onboarding",
    },
    {
      id: "sources",
      title: "Source-grounded references",
      detail:
        input.referenceSources.length > 0
          ? `${input.referenceSources.length} source file(s) attached for grounded citations.`
          : "Attach at least one paper, prior proposal, or reviewer note.",
      status: input.referenceSources.length > 0 ? "ready" : "blocked",
      action: "upload-first",
    },
    {
      id: "draft",
      title: "Draft coverage",
      detail: `${draftedCount}/${SECTION_ORDER.length} core sections drafted.`,
      status:
        draftedCount === SECTION_ORDER.length
          ? "ready"
          : draftedCount > 0
          ? "in_progress"
          : "blocked",
      action: "/preview",
    },
    {
      id: "approvals",
      title: "Section approvals",
      detail: `${approvedCount}/${SECTION_ORDER.length} sections approved.`,
      status:
        approvedCount === SECTION_ORDER.length
          ? "ready"
          : approvedCount > 0
          ? "in_progress"
          : "blocked",
      action: "/approve",
    },
    {
      id: "compliance-run",
      title: "Compliance check run",
      detail: input.validation.lastRun
        ? `Last run at ${new Date(input.validation.lastRun).toLocaleString()}. ${input.validation.failed.length} blocker(s), ${input.validation.warnings.length} warning(s).`
        : "Run validation to get blocker list.",
      status: input.validation.lastRun ? "ready" : "blocked",
      action: "/validate",
    },
    {
      id: "submission-gate",
      title: "Submission gate",
      detail: input.validation.readyForSubmission
        ? "No hard blockers detected. Ready for final assembly."
        : "Resolve compliance blockers before submission.",
      status: input.validation.readyForSubmission ? "ready" : "blocked",
      action: "open-compliance",
    },
  ];

  const blockerCount = items.filter((item) => item.status === "blocked").length;
  const inProgressCount = items.filter((item) => item.status === "in_progress").length;
  const scoreRaw = items.reduce((sum, item) => {
    if (item.status === "ready") return sum + 1;
    if (item.status === "in_progress") return sum + 0.5;
    return sum;
  }, 0);

  return {
    score: Math.round((scoreRaw / items.length) * 100),
    blockers: blockerCount,
    inProgress: inProgressCount,
    ready: blockerCount === 0,
    items,
  };
}
