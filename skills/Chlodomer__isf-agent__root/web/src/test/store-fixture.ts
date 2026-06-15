import { useProposalStore } from "@/lib/store";

function createInitialData() {
  return {
    session: {
      id: null,
      started: null,
      lastUpdated: null,
      currentPhase: 1 as const,
    },
    requirements: {
      fetched: false,
      sourceUrl: null,
      fetchDate: null,
      eligibility: {
        positionRequirement: null,
        yearsSinceAppointment: null,
        institutionRequirement: null,
        priorFundingRestriction: null,
      },
      budget: { annualMaximum: null, totalMaximum: null, currency: "NIS" },
      duration: null,
      deadline: null,
      pageLimits: { total: null, background: null, methods: null, cv: null },
      requiredSections: [],
      formatting: { language: null, font: null, margins: null, fileFormat: null },
    },
    researcherInfo: {
      name: null,
      institution: null,
      department: null,
      position: null,
      appointmentDate: null,
      priorPositions: [],
      priorIsfFunding: null,
      email: null,
    },
    projectInfo: {
      title: null,
      centralQuestion: null,
      aims: [
        { number: 1, title: null, hypothesis: null, approach: null },
        { number: 2, title: null, hypothesis: null, approach: null },
      ],
      innovation: null,
      preliminaryData: null,
      methodology: null,
      expectedOutcomes: null,
      risks: [],
      duration: null,
      milestones: { year1: [], year2: [], year3: [], year4: [] },
    },
    resources: {
      personnel: [],
      equipment: [],
      consumables: [],
      travel: [],
      other: [],
      budgetTotals: {
        year1: null,
        year2: null,
        year3: null,
        year4: null,
        total: null,
      },
    },
    trackRecord: {
      publications: [],
      relevantPublications: [],
      priorGrants: [],
      collaborators: [],
    },
    referenceSources: [],
    proposalSections: {
      abstract: { draft: null, approved: false, wordCount: null },
      background: { draft: null, approved: false, pageCount: null },
      aims: { draft: null, approved: false },
      methods: { draft: null, approved: false, pageCount: null },
      innovation: { draft: null, approved: false },
      budget: { draft: null, approved: false },
      risks: { draft: null, approved: false },
      bibliography: { entries: [] },
    },
    interview: {
      currentSection: null,
      currentQuestion: null,
      completedSections: [],
      skippedQuestions: [],
    },
    validation: {
      lastRun: null,
      passed: [],
      failed: [],
      warnings: [],
      manualReview: [],
      readyForSubmission: false,
    },
    learnings: {
      successfulPatterns: [],
      weaknesses: [],
      reviewerConcerns: [],
      redFlags: [],
    },
    versionHistory: [],
    messages: [],
    ui: {
      contextPanelOpen: false,
      activeContextTab: "operations" as const,
      leftRailCollapsed: false,
    },
  };
}

type StoreState = ReturnType<typeof useProposalStore.getState>;

export function resetProposalStore() {
  const state = useProposalStore.getState();
  useProposalStore.setState(
    {
      ...state,
      ...createInitialData(),
    },
    true
  );
}

export function patchProposalStore(partial: Partial<StoreState>) {
  useProposalStore.setState(partial);
}
