import type { ChatMessage } from "./types";

interface LocalAgentContext {
  name?: string | null;
  affiliation?: string | null;
}

function isOnboardingRequest(input: string): boolean {
  return (
    input === "/onboarding" ||
    input === "/start" ||
    input.includes("how do i use") ||
    input.includes("how to use") ||
    input.includes("onboarding") ||
    input.includes("what can i do")
  );
}

function isDocsRequest(input: string): boolean {
  return (
    input === "/isf-docs" ||
    input.includes("isf docs") ||
    input.includes("isf documentation") ||
    input.includes("grant docs") ||
    input.includes("guidelines")
  );
}

function isProcessRequest(input: string): boolean {
  return (
    input === "/isf-process" ||
    input.includes("isf process") ||
    input.includes("application process") ||
    input.includes("how to apply") ||
    input.includes("submission process")
  );
}

function isHelpRequest(input: string): boolean {
  return input === "/help" || input === "help";
}

export function getLocalAgentReply(rawInput: string, context?: LocalAgentContext): string | null {
  const normalized = rawInput.trim().toLowerCase();
  const namePrefix = context?.name?.trim() ? `${context.name.trim()}, ` : "";
  const affiliationNote = context?.affiliation?.trim()
    ? `Context: ${context.affiliation.trim()}.`
    : null;

  if (isOnboardingRequest(normalized)) {
    return [
      `${namePrefix}quick onboarding:`,
      "1. Share your project summary and target grant track.",
      "2. You can type in plain language. No special command syntax is required.",
      "3. Upload papers/proposals/reviews with the paperclip so drafts stay evidence-based.",
      "4. Use Compliance and Readiness views to catch blockers before submission.",
      "5. If needed, optional shortcuts are available (for example /validate, /readiness).",
      ...(affiliationNote ? [affiliationNote] : []),
    ].join("\n");
  }

  if (isDocsRequest(normalized)) {
    return [
      "ISF docs are available locally.",
      "Index: .context/isf-grants-docs/manifest.json",
      "Files: .context/isf-grants-docs/files/",
      "Text: .context/isf-grants-docs/text/",
      "Refresh with: node scripts/fetch-isf-grants-docs.mjs",
    ].join("\n");
  }

  if (isProcessRequest(normalized)) {
    return [
      "ISF process:",
      "1. Confirm eligibility and program fit.",
      "2. Register the proposal in the ISF system.",
      "3. Prepare proposal files and compliant budget.",
      "4. Submit before deadline with institutional approval.",
      "5. Peer review, committee decision, then revise/resubmit if needed.",
    ].join("\n");
  }

  if (isHelpRequest(normalized)) {
    return [
      "Quick commands: /onboarding, /sources, /validate, /readiness, /checklist, /preview, /status, /requirements, /isf-docs, /isf-process",
    ].join("\n");
  }

  return null;
}

export function buildLocalAgentReply(rawInput: string, context?: LocalAgentContext): ChatMessage | null {
  const content = getLocalAgentReply(rawInput, context);
  if (!content) return null;

  return {
    id: `agent-${Date.now()}-${Math.floor(Math.random() * 10000)}`,
    type: "text",
    role: "agent",
    content,
  };
}
