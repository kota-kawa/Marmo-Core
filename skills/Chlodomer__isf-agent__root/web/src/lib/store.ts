import { create } from "zustand";
import {
  advanceInterviewAfterUserResponse,
  countCharacters,
  countWords,
  estimatePagesFromWords,
} from "./workflow-sync";
import type {
  Session,
  Requirements,
  ResearcherInfo,
  ProjectInfo,
  Resources,
  TrackRecord,
  ProposalSections,
  InterviewState,
  ValidationState,
  Learnings,
  VersionSnapshot,
  UIState,
  ChatMessage,
  Phase,
  ContextTab,
  SectionName,
  ReferenceSource,
} from "./types";

interface ProposalStore {
  // Domain state (maps to state-template.yaml)
  session: Session;
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
  versionHistory: VersionSnapshot[];

  // Chat state
  messages: ChatMessage[];

  // Persistence
  chatPersistenceConsent: boolean | null;

  // UI state
  ui: UIState;

  // Actions
  resetWorkspaceForNewThread: () => void;
  setChatPersistenceConsent: (consent: boolean | null) => void;
  setPhase: (phase: Phase) => void;
  setRequirementsFetched: (input: {
    fetched: boolean;
    sourceUrl?: string | null;
    fetchDate?: string | null;
  }) => void;
  setResearcherInfo: (info: Partial<ResearcherInfo>) => void;
  addMessage: (message: ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
  updateMessage: (id: string, content: string) => void;
  toggleContextPanel: () => void;
  setContextTab: (tab: ContextTab) => void;
  openContextPanel: (tab: ContextTab) => void;
  setLeftRailCollapsed: (collapsed: boolean) => void;
  setSectionDraft: (section: SectionName, draft: string) => void;
  approveSection: (section: SectionName) => void;
  setSectionApproval: (section: SectionName, approved: boolean) => void;
  updateInterviewProgress: (section: number, question: number) => void;
  recordInterviewAnswer: () => void;
  completeInterviewSection: (section: number) => void;
  skipQuestion: (section: number, question: number) => void;
  setValidation: (validation: Partial<ValidationState>) => void;
  addLearningPattern: (pattern: Learnings["successfulPatterns"][0]) => void;
  addWeakness: (weakness: Learnings["weaknesses"][0]) => void;
  addReviewerConcern: (concern: Learnings["reviewerConcerns"][0]) => void;
  addReferenceSources: (sources: ReferenceSource[]) => void;
  setVersionHistory: (snapshots: VersionSnapshot[]) => void;
  captureWorkspaceSnapshot: (label?: string, reason?: "manual" | "auto") => VersionSnapshot;
  restoreWorkspaceSnapshot: (snapshotId: string) => boolean;
}

const initialSession: Session = {
  id: null,
  started: null,
  lastUpdated: null,
  currentPhase: 1,
};

const initialRequirements: Requirements = {
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
};

const initialResearcherInfo: ResearcherInfo = {
  name: null,
  institution: null,
  department: null,
  position: null,
  appointmentDate: null,
  priorPositions: [],
  priorIsfFunding: null,
  email: null,
};

const initialProjectInfo: ProjectInfo = {
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
};

const initialResources: Resources = {
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
};

const initialTrackRecord: TrackRecord = {
  publications: [],
  relevantPublications: [],
  priorGrants: [],
  collaborators: [],
};

const emptySection = { draft: null, approved: false };

const initialProposalSections: ProposalSections = {
  abstract: { ...emptySection, wordCount: null, charCount: null, pageCount: null },
  background: { ...emptySection, wordCount: null, charCount: null, pageCount: null },
  aims: { ...emptySection, wordCount: null, charCount: null, pageCount: null },
  methods: { ...emptySection, wordCount: null, charCount: null, pageCount: null },
  innovation: { ...emptySection, wordCount: null, charCount: null, pageCount: null },
  budget: { ...emptySection, wordCount: null, charCount: null, pageCount: null },
  risks: { ...emptySection, wordCount: null, charCount: null, pageCount: null },
  bibliography: { entries: [] },
};

const initialInterview: InterviewState = {
  currentSection: null,
  currentQuestion: null,
  completedSections: [],
  skippedQuestions: [],
};

const initialValidation: ValidationState = {
  lastRun: null,
  passed: [],
  failed: [],
  warnings: [],
  manualReview: [],
  readyForSubmission: false,
};

const initialLearnings: Learnings = {
  successfulPatterns: [],
  weaknesses: [],
  reviewerConcerns: [],
  redFlags: [],
};

const initialVersionHistory: VersionSnapshot[] = [];

const initialUI: UIState = {
  contextPanelOpen: false,
  activeContextTab: "operations",
  leftRailCollapsed: false,
};

function touchSession(session: Session): Session {
  const now = new Date().toISOString();
  return {
    ...session,
    started: session.started ?? now,
    lastUpdated: now,
  };
}

function cloneJson<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

export const useProposalStore = create<ProposalStore>((set) => ({
  session: initialSession,
  requirements: initialRequirements,
  researcherInfo: initialResearcherInfo,
  projectInfo: initialProjectInfo,
  resources: initialResources,
  trackRecord: initialTrackRecord,
  referenceSources: [],
  proposalSections: initialProposalSections,
  interview: initialInterview,
  validation: initialValidation,
  learnings: initialLearnings,
  versionHistory: initialVersionHistory,
  messages: [],
  chatPersistenceConsent: null,
  ui: initialUI,

  resetWorkspaceForNewThread: () =>
    set((state) => ({
      session: {
        ...initialSession,
        started: new Date().toISOString(),
        lastUpdated: new Date().toISOString(),
      },
      requirements: initialRequirements,
      projectInfo: initialProjectInfo,
      resources: initialResources,
      trackRecord: initialTrackRecord,
      referenceSources: [],
      proposalSections: initialProposalSections,
      interview: initialInterview,
      validation: initialValidation,
      learnings: initialLearnings,
      versionHistory: initialVersionHistory,
      ui: {
        ...state.ui,
        activeContextTab: "operations",
      },
    })),

  setChatPersistenceConsent: (consent) =>
    set((state) => ({
      chatPersistenceConsent: consent,
      session: touchSession(state.session),
    })),

  setPhase: (phase) =>
    set((state) => ({
      session: { ...touchSession(state.session), currentPhase: phase },
    })),

  setRequirementsFetched: (input) =>
    set((state) => ({
      requirements: {
        ...state.requirements,
        fetched: input.fetched,
        sourceUrl: input.sourceUrl ?? state.requirements.sourceUrl,
        fetchDate: input.fetchDate ?? (input.fetched ? new Date().toISOString() : state.requirements.fetchDate),
      },
      session: touchSession(state.session),
    })),

  setResearcherInfo: (info) =>
    set((state) => ({
      researcherInfo: {
        ...state.researcherInfo,
        ...info,
      },
      session: touchSession(state.session),
    })),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
      session: touchSession(state.session),
    })),

  setMessages: (messages) =>
    set((state) => ({
      messages,
      session: touchSession(state.session),
    })),

  updateMessage: (id, content) =>
    set((state) => ({
      messages: state.messages.map((msg) =>
        msg.id === id && msg.type === "text"
          ? { ...msg, content }
          : msg
      ),
      session: touchSession(state.session),
    })),

  toggleContextPanel: () =>
    set((state) => ({
      ui: { ...state.ui, contextPanelOpen: !state.ui.contextPanelOpen },
    })),

  setContextTab: (tab) =>
    set((state) => ({
      ui: { ...state.ui, activeContextTab: tab },
    })),

  openContextPanel: (tab) =>
    set((state) => ({
      ui: { ...state.ui, contextPanelOpen: true, activeContextTab: tab },
    })),

  setLeftRailCollapsed: (collapsed) =>
    set((state) => ({
      ui: { ...state.ui, leftRailCollapsed: collapsed },
    })),

  setSectionDraft: (section, draft) =>
    set((state) => {
      const trimmed = draft.trim();
      const wordCount = countWords(trimmed);
      return {
        proposalSections: {
          ...state.proposalSections,
          [section]: {
            ...state.proposalSections[section],
            draft: trimmed,
            wordCount,
            charCount: countCharacters(trimmed),
            pageCount: estimatePagesFromWords(wordCount),
            approved: false,
          },
        },
        session: touchSession(state.session),
      };
    }),

  approveSection: (section) =>
    set((state) => ({
      proposalSections: {
        ...state.proposalSections,
        [section]: { ...state.proposalSections[section], approved: true },
      },
      session: touchSession(state.session),
    })),

  setSectionApproval: (section, approved) =>
    set((state) => ({
      proposalSections: {
        ...state.proposalSections,
        [section]: { ...state.proposalSections[section], approved },
      },
      session: touchSession(state.session),
    })),

  updateInterviewProgress: (section, question) =>
    set((state) => ({
      interview: {
        ...state.interview,
        currentSection: section,
        currentQuestion: question,
      },
      session: touchSession(state.session),
    })),

  recordInterviewAnswer: () =>
    set((state) => ({
      interview: advanceInterviewAfterUserResponse(state.interview),
      session: touchSession(state.session),
    })),

  completeInterviewSection: (section) =>
    set((state) => ({
      interview: {
        ...state.interview,
        completedSections: state.interview.completedSections.includes(section)
          ? state.interview.completedSections
          : [...state.interview.completedSections, section],
      },
      session: touchSession(state.session),
    })),

  skipQuestion: (section, question) =>
    set((state) => ({
      interview: {
        ...state.interview,
        skippedQuestions: [
          ...state.interview.skippedQuestions,
          { section, question },
        ],
      },
      session: touchSession(state.session),
    })),

  setValidation: (validation) =>
    set((state) => ({
      validation: { ...state.validation, ...validation },
      session: touchSession(state.session),
    })),

  addLearningPattern: (pattern) =>
    set((state) => ({
      learnings: {
        ...state.learnings,
        successfulPatterns: [...state.learnings.successfulPatterns, pattern],
      },
      session: touchSession(state.session),
    })),

  addWeakness: (weakness) =>
    set((state) => ({
      learnings: {
        ...state.learnings,
        weaknesses: [...state.learnings.weaknesses, weakness],
      },
      session: touchSession(state.session),
    })),

  addReviewerConcern: (concern) =>
    set((state) => ({
      learnings: {
        ...state.learnings,
        reviewerConcerns: [...state.learnings.reviewerConcerns, concern],
      },
      session: touchSession(state.session),
    })),

  addReferenceSources: (sources) =>
    set((state) => {
      const existingIds = new Set(state.referenceSources.map((source) => source.id));
      const uniqueSources = sources.filter((source) => !existingIds.has(source.id));
      if (uniqueSources.length === 0) {
        return {};
      }
      return {
        referenceSources: [...state.referenceSources, ...uniqueSources],
        session: touchSession(state.session),
      };
    }),

  setVersionHistory: (snapshots) =>
    set((state) => ({
      versionHistory: snapshots.slice(0, 30),
      session: touchSession(state.session),
    })),

  captureWorkspaceSnapshot: (label = "Restore point", reason = "manual") => {
    const state = useProposalStore.getState();
    const snapshot: VersionSnapshot = {
      id: `snapshot-${Date.now()}-${Math.floor(Math.random() * 10000)}`,
      label,
      reason,
      createdAt: new Date().toISOString(),
      phase: state.session.currentPhase,
      state: {
        phase: state.session.currentPhase,
        requirements: cloneJson(state.requirements),
        researcherInfo: cloneJson(state.researcherInfo),
        projectInfo: cloneJson(state.projectInfo),
        resources: cloneJson(state.resources),
        trackRecord: cloneJson(state.trackRecord),
        referenceSources: cloneJson(state.referenceSources),
        proposalSections: cloneJson(state.proposalSections),
        interview: cloneJson(state.interview),
        validation: cloneJson(state.validation),
        learnings: cloneJson(state.learnings),
      },
    };

    set((current) => ({
      versionHistory: [snapshot, ...current.versionHistory].slice(0, 30),
      session: touchSession(current.session),
    }));

    return snapshot;
  },

  restoreWorkspaceSnapshot: (snapshotId) => {
    const current = useProposalStore.getState();
    const snapshot = current.versionHistory.find((entry) => entry.id === snapshotId);
    if (!snapshot) return false;

    set((state) => ({
      session: {
        ...touchSession(state.session),
        currentPhase: snapshot.state.phase,
      },
      requirements: cloneJson(snapshot.state.requirements),
      researcherInfo: cloneJson(snapshot.state.researcherInfo),
      projectInfo: cloneJson(snapshot.state.projectInfo),
      resources: cloneJson(snapshot.state.resources),
      trackRecord: cloneJson(snapshot.state.trackRecord),
      referenceSources: cloneJson(snapshot.state.referenceSources),
      proposalSections: cloneJson(snapshot.state.proposalSections),
      interview: cloneJson(snapshot.state.interview),
      validation: cloneJson(snapshot.state.validation),
      learnings: cloneJson(snapshot.state.learnings),
    }));

    return true;
  },
}));
