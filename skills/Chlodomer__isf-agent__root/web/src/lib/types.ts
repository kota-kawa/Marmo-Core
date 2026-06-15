// Types derived from state-template.yaml

export type Phase = 1 | 2 | 3 | 4 | 5 | 6 | 7;

export const PHASE_LABELS: Record<Phase, string> = {
  1: "Getting Started",
  2: "ISF Requirements",
  3: "Learn from Past Work",
  4: "Research Interview",
  5: "Draft Proposal",
  6: "Compliance Check",
  7: "Final Assembly",
};

// --- Session ---

export interface Session {
  id: string | null;
  started: string | null;
  lastUpdated: string | null;
  currentPhase: Phase;
}

// --- Requirements ---

export interface Eligibility {
  positionRequirement: string | null;
  yearsSinceAppointment: number | null;
  institutionRequirement: string | null;
  priorFundingRestriction: string | null;
}

export interface BudgetLimits {
  annualMaximum: number | null;
  totalMaximum: number | null;
  currency: string;
}

export interface PageLimits {
  total: number | null;
  background: number | null;
  methods: number | null;
  cv: number | null;
}

export interface Formatting {
  language: string | null;
  font: string | null;
  margins: string | null;
  fileFormat: string | null;
}

export interface Requirements {
  fetched: boolean;
  sourceUrl: string | null;
  fetchDate: string | null;
  eligibility: Eligibility;
  budget: BudgetLimits;
  duration: number | null;
  deadline: string | null;
  pageLimits: PageLimits;
  requiredSections: string[];
  formatting: Formatting;
}

// --- Researcher Info ---

export interface ResearcherInfo {
  name: string | null;
  institution: string | null;
  department: string | null;
  position: string | null;
  appointmentDate: string | null;
  priorPositions: string[];
  priorIsfFunding: string | null;
  email: string | null;
}

// --- Project Info ---

export interface Aim {
  number: number;
  title: string | null;
  hypothesis: string | null;
  approach: string | null;
}

export interface Risk {
  risk: string | null;
  likelihood: "low" | "medium" | "high" | null;
  mitigation: string | null;
}

export interface Milestones {
  year1: string[];
  year2: string[];
  year3: string[];
  year4: string[];
}

export interface ProjectInfo {
  title: string | null;
  centralQuestion: string | null;
  aims: Aim[];
  innovation: string | null;
  preliminaryData: string | null;
  methodology: string | null;
  expectedOutcomes: string | null;
  risks: Risk[];
  duration: number | null;
  milestones: Milestones;
}

// --- Resources ---

export interface Personnel {
  role: string | null;
  percentage: number | null;
  years: number | null;
  annualCost: number | null;
  justification: string | null;
}

export interface Equipment {
  item: string | null;
  cost: number | null;
  justification: string | null;
}

export interface Consumable {
  category: string | null;
  annualCost: number | null;
  justification: string | null;
}

export interface Travel {
  type: string | null;
  annualCost: number | null;
  justification: string | null;
}

export interface BudgetTotals {
  year1: number | null;
  year2: number | null;
  year3: number | null;
  year4: number | null;
  total: number | null;
}

export interface Resources {
  personnel: Personnel[];
  equipment: Equipment[];
  consumables: Consumable[];
  travel: Travel[];
  other: string[];
  budgetTotals: BudgetTotals;
}

// --- Track Record ---

export interface RelevantPublication {
  citation: string | null;
  relevance: string | null;
}

export interface PriorGrant {
  agency: string | null;
  title: string | null;
  amount: number | null;
  period: string | null;
  role: string | null;
}

export interface Collaborator {
  name: string | null;
  institution: string | null;
  expertise: string | null;
  role: string | null;
  letterOfSupport: boolean;
}

export interface TrackRecord {
  publications: string[];
  relevantPublications: RelevantPublication[];
  priorGrants: PriorGrant[];
  collaborators: Collaborator[];
}

// --- Source Grounding ---

export interface ReferenceSource {
  id: string;
  label: string;
  filename: string;
  mimeType: string;
  size: number;
  addedAt: string;
}

// --- Proposal Sections ---

export interface SectionDraft {
  draft: string | null;
  approved: boolean;
  wordCount?: number | null;
  charCount?: number | null;
  pageCount?: number | null;
}

export interface ProposalSections {
  abstract: SectionDraft;
  background: SectionDraft;
  aims: SectionDraft;
  methods: SectionDraft;
  innovation: SectionDraft;
  budget: SectionDraft;
  risks: SectionDraft;
  bibliography: { entries: string[] };
}

export type SectionName = keyof Omit<ProposalSections, "bibliography">;

export const SECTION_ORDER: SectionName[] = [
  "abstract",
  "background",
  "aims",
  "methods",
  "innovation",
  "budget",
  "risks",
];

export const SECTION_LABELS: Record<SectionName, string> = {
  abstract: "Abstract",
  background: "Scientific Background",
  aims: "Specific Aims",
  methods: "Research Plan & Methods",
  innovation: "Innovation & Significance",
  budget: "Budget & Justification",
  risks: "Risk Mitigation",
};

// --- Interview ---

export interface InterviewSkippedQuestion {
  section: number;
  question: number;
}

export interface InterviewState {
  currentSection: number | null;
  currentQuestion: number | null;
  completedSections: number[];
  skippedQuestions: InterviewSkippedQuestion[];
}

export const INTERVIEW_SECTIONS = [
  { id: 1, label: "Eligibility & Background", totalQuestions: 5 },
  { id: 2, label: "Research Core", totalQuestions: 8 },
  { id: 3, label: "Resources & Timeline", totalQuestions: 5 },
  { id: 4, label: "Track Record", totalQuestions: 4 },
] as const;

export const TOTAL_INTERVIEW_QUESTIONS = INTERVIEW_SECTIONS.reduce(
  (sum, section) => sum + section.totalQuestions,
  0
);

// --- Validation ---

export interface ComplianceIssue {
  id: string;
  category: string;
  name: string;
  description: string;
  severity: "failed" | "warning";
  fix?: string;
}

export interface ValidationState {
  lastRun: string | null;
  passed: string[];
  failed: ComplianceIssue[];
  warnings: ComplianceIssue[];
  manualReview: string[];
  readyForSubmission: boolean;
}

// --- Learnings ---

export interface SuccessfulPattern {
  id: string;
  category: string;
  description: string;
  example: string;
  application: string;
  appliedTo: string | null;
}

export interface Weakness {
  id: string;
  category: string;
  description: string;
  quote: string;
  prevention: string;
}

export interface ReviewerConcern {
  concern: string;
  frequency: number;
  severity: "critical" | "moderate";
  addressable: boolean;
  prevention: string;
}

export interface RedFlag {
  phrase: string;
  count: number;
  problem: string;
}

export interface Learnings {
  successfulPatterns: SuccessfulPattern[];
  weaknesses: Weakness[];
  reviewerConcerns: ReviewerConcern[];
  redFlags: RedFlag[];
}

// --- Version Snapshots ---

export interface SnapshotWorkspaceState {
  phase: Phase;
  requirements: Requirements;
  researcherInfo: ResearcherInfo;
  projectInfo: ProjectInfo;
  resources: Resources;
  trackRecord: TrackRecord;
  referenceSources: ReferenceSource[];
  proposalSections: ProposalSections;
  interview: InterviewState;
  validation: ValidationState;
  learnings: Learnings;
}

export interface VersionSnapshot {
  id: string;
  label: string;
  reason: "manual" | "auto";
  createdAt: string;
  phase: Phase;
  state: SnapshotWorkspaceState;
}

// --- Chat Messages ---

export type ChallengeIntensity = 1 | 2 | 3;

export type ChatMessage =
  | { id: string; type: "text"; role: "agent" | "user"; content: string }
  | {
      id: string;
      type: "challenge";
      role: "agent";
      category: string;
      intensity: ChallengeIntensity;
      question: string;
      context: string;
    }
  | {
      id: string;
      type: "interview_question";
      role: "agent";
      section: number;
      questionNum: number;
      totalInSection: number;
      question: string;
      guidance?: string;
      example?: string;
    }
  | {
      id: string;
      type: "draft_review";
      role: "agent";
      sectionName: SectionName;
      version: number;
      wordCount: number;
      pageEstimate: number;
      patternsApplied: string[];
      concernsAddressed: string[];
      content: string;
    }
  | {
      id: string;
      type: "compliance_report";
      role: "agent";
      passed: number;
      failed: ComplianceIssue[];
      warnings: ComplianceIssue[];
    }
  | {
      id: string;
      type: "learning_summary";
      role: "agent";
      proposalName: string;
      outcome: "funded" | "rejected";
      patterns?: SuccessfulPattern[];
      weaknesses?: Weakness[];
      redFlags?: RedFlag[];
    }
  | {
      id: string;
      type: "phase_transition";
      role: "agent";
      fromPhase: Phase;
      toPhase: Phase;
      summary: string;
    }
  | { id: string; type: "welcome"; role: "agent" }
  | {
      id: string;
      type: "resume_session";
      role: "agent";
      proposalTitle: string | null;
      currentPhase: Phase;
      completedPhases: Phase[];
      lastActive: string;
    }
  | { id: string; type: "file_upload"; role: "agent" };

// --- UI State ---

export type ContextTab =
  | "operations"
  | "draft"
  | "learnings"
  | "compliance"
  | "interview"
  | "readiness"
  | "history";

export interface UIState {
  contextPanelOpen: boolean;
  activeContextTab: ContextTab;
  leftRailCollapsed: boolean;
}
