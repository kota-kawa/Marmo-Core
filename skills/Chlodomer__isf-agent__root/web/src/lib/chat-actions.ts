import type { Phase } from "./types";

export interface SuggestedAction {
  label: string;
  command: string;
  variant?: "default" | "approve" | "danger";
}

export function getSuggestedActions(phase: Phase, context?: { draftReady?: boolean }): SuggestedAction[] {
  switch (phase) {
    case 1:
      return [
        { label: "Quick Onboarding", command: "/onboarding" },
        { label: "Upload Past Proposal", command: "/learn-from-grant" },
        { label: "Explain ISF Process", command: "/isf-process" },
        { label: "Connect Google Drive", command: "/connect-drive" },
        { label: "View Requirements", command: "/requirements" },
      ];
    case 2:
      return [
        { label: "View Requirements", command: "/requirements" },
        { label: "Explain ISF Process", command: "/isf-process" },
        { label: "Open ISF Docs Index", command: "/isf-docs" },
        { label: "Upload Past Proposal", command: "/learn-from-grant" },
      ];
    case 3:
      return [
        { label: "Upload Past Proposal", command: "/learn-from-grant" },
        { label: "List Sources", command: "/sources" },
        { label: "Add Reviewer Feedback", command: "/learn-from-reviews" },
        { label: "Show Learnings", command: "/show-learnings" },
      ];
    case 4:
      return [
        { label: "Skip Question", command: "/skip" },
        { label: "Go Back", command: "/back" },
        { label: "Challenge Me", command: "/challenge" },
        { label: "List Sources", command: "/sources" },
        { label: "Preview Draft", command: "/preview" },
        { label: "Show Learnings", command: "/show-learnings" },
      ];
    case 5:
      return [
        ...(context?.draftReady
          ? [
              { label: "Approve Section", command: "/approve", variant: "approve" as const },
              { label: "Request Changes", command: "/revise" },
            ]
          : []),
        { label: "Compare to Past", command: "/compare" },
        { label: "Check Red Flags", command: "/redflags" },
        { label: "Readiness", command: "/readiness" },
        { label: "Devil's Advocate", command: "/devil" },
        { label: "Preview Full", command: "/preview" },
      ];
    case 6:
      return [
        { label: "Fix Issues", command: "/fix" },
        { label: "View Full Report", command: "/compliance" },
        { label: "Readiness", command: "/readiness" },
        { label: "Re-run Check", command: "/validate" },
      ];
    case 7:
      return [
        { label: "Preview Final", command: "/preview" },
        { label: "Export PDF", command: "/export" },
        { label: "Readiness", command: "/readiness" },
        { label: "Submission Checklist", command: "/checklist" },
      ];
    default:
      return [];
  }
}

export function getNextActionText(
  phase: Phase,
  interviewProgress?: { remaining: number; sectionLabel: string },
  sectionsDrafted?: number,
  complianceIssues?: number
): string {
  switch (phase) {
    case 1:
      return "Upload past proposals to help the agent learn your patterns";
    case 2:
      return "Review ISF requirements and confirm your eligibility";
    case 3:
      return "Review the learnings extracted from your past proposals";
    case 4:
      return interviewProgress
        ? `Answer ${interviewProgress.remaining} remaining questions in ${interviewProgress.sectionLabel}`
        : "Begin the structured research interview";
    case 5:
      return sectionsDrafted !== undefined
        ? `Draft and review ${7 - sectionsDrafted} remaining proposal sections`
        : "Begin drafting your proposal sections";
    case 6:
      return complianceIssues
        ? `Fix ${complianceIssues} compliance issues before final assembly`
        : "Run compliance validation on your proposal";
    case 7:
      return "Compile and export your final proposal";
    default:
      return "";
  }
}
