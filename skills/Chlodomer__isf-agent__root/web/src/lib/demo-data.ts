import type { ChatMessage, Phase } from "./types";

/**
 * Demo messages showcasing all card types.
 * In production, these would come from the AI backend.
 */
export const DEMO_MESSAGES: ChatMessage[] = [
  { id: "demo-welcome-1", type: "welcome", role: "agent" },
  {
    id: "demo-text-1",
    type: "text",
    role: "user",
    content: "I'd like to start fresh. I'm working on a proposal about neural mechanisms of decision-making.",
  },
  {
    id: "demo-text-2",
    type: "text",
    role: "agent",
    content:
      "Great, let's get started! Before we dive into details, I want to challenge your thinking on three fundamentals. These are the hard questions that reviewers will ask — better to address them now.",
  },
  {
    id: "demo-challenge-1",
    type: "challenge",
    role: "agent",
    category: "Innovation",
    intensity: 2,
    question:
      "What makes your approach genuinely novel, not just incremental? A skeptical reviewer might say this is just computational modeling applied to a well-studied domain.",
    context:
      "Tests defensibility of your innovation claim. Reviewers consistently flag proposals that don't clearly differentiate from prior work.",
  },
  {
    id: "demo-text-3",
    type: "text",
    role: "user",
    content:
      "Our approach combines real-time neural recording with a novel Bayesian framework that can track value computations at the single-trial level. Unlike existing methods that aggregate across trials, we capture the dynamics of individual decisions. This hasn't been possible before because we developed a new denoising algorithm in our pilot work.",
  },
  {
    id: "demo-text-4",
    type: "text",
    role: "agent",
    content:
      "Solid response — you've named a specific technical advance (single-trial decoding via your denoising algorithm) and explained why existing approaches can't do this. I'll make sure this innovation is prominent in your proposal. Let's move to the requirements check.",
  },
  {
    id: "demo-transition-1",
    type: "phase_transition",
    role: "agent",
    fromPhase: 1 as Phase,
    toPhase: 2 as Phase,
    summary:
      "Initialization complete. Foundational challenges addressed: innovation framing is strong, feasibility grounded in pilot data, significance tied to clinical applications.",
  },
  {
    id: "demo-interview-1",
    type: "interview_question",
    role: "agent",
    section: 2,
    questionNum: 3,
    totalInSection: 8,
    question: "What are your specific aims? Most ISF proposals have 2-4 aims. Each aim should be specific, measurable, and independent enough to succeed on its own.",
    guidance:
      "Aim independence is critical — reviewers worry about cascading failure if aims depend on each other. Think about what you'd deliver even if one aim fails completely.",
    example:
      'Aim 1: Characterize the neural representations of subjective value during risky choices using single-trial EEG decoding. Aim 2: Test whether value signals in prefrontal cortex causally influence choice through targeted TMS disruption.',
  },
  {
    id: "demo-learning-1",
    type: "learning_summary",
    role: "agent",
    proposalName: "2023_decision_making",
    outcome: "funded",
    patterns: [
      {
        id: "SP-001",
        category: "abstract_structure",
        description: "Opens with societal impact before scientific gap",
        example: "",
        application: "Use impact-first opening in abstracts",
        appliedTo: null,
      },
      {
        id: "SP-002",
        category: "aim_structure",
        description: "Each aim has explicit contingency plan and standalone deliverable",
        example: "",
        application: "Include fallback for every aim",
        appliedTo: null,
      },
      {
        id: "SP-003",
        category: "preliminary_data",
        description: "Specific statistics cited (N=45, ICC=0.78) rather than vague references",
        example: "",
        application: "Include exact numbers from pilot data",
        appliedTo: null,
      },
    ],
  },
  {
    id: "demo-draft-1",
    type: "draft_review",
    role: "agent",
    sectionName: "abstract",
    version: 1,
    wordCount: 287,
    pageEstimate: 1,
    patternsApplied: [
      "Impact-first opening (from 2023 funded proposal)",
      "Structured aim listing with deliverables",
      "Specific pilot data statistics (N=45)",
    ],
    concernsAddressed: [
      "Reviewer concern: methodology specificity",
      "Reviewer concern: aim independence",
    ],
    content: "[Abstract content would appear in the context panel]",
  },
  {
    id: "demo-compliance-1",
    type: "compliance_report",
    role: "agent",
    passed: 24,
    failed: [
      {
        id: "STRUCT-02",
        category: "Structure",
        name: "Abstract Length",
        description: "Abstract is 315 words (maximum: 300 words). Need to cut 15 words.",
        severity: "failed",
      },
      {
        id: "BUDGET-01",
        category: "Budget",
        name: "Annual Maximum",
        description: "Year 2 budget is NIS 285,000 (maximum: NIS 250,000). Exceeds limit by NIS 35,000.",
        severity: "failed",
      },
    ],
    warnings: [
      {
        id: "QUAL-02",
        category: "Quality",
        name: "Timeline Distribution",
        description: "70% of milestones are concentrated in Year 1. Consider distributing more evenly.",
        severity: "warning",
      },
    ],
  },
];
