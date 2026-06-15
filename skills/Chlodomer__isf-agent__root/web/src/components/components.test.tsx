import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";
import ChatInput from "@/components/chat/ChatInput";
import MainChat from "@/components/chat/MainChat";
import MessageThread from "@/components/chat/MessageThread";
import NextActionBanner from "@/components/chat/NextActionBanner";
import SuggestedActionsBar from "@/components/chat/SuggestedActionsBar";
import WorkflowTransparencyDeck from "@/components/chat/WorkflowTransparencyDeck";
import ChallengeCard from "@/components/chat/messages/ChallengeCard";
import ComplianceReportCard from "@/components/chat/messages/ComplianceReportCard";
import DraftReviewBlock from "@/components/chat/messages/DraftReviewBlock";
import FileUploadCard from "@/components/chat/messages/FileUploadCard";
import InterviewQuestionBlock from "@/components/chat/messages/InterviewQuestionBlock";
import LearningSummaryCard from "@/components/chat/messages/LearningSummaryCard";
import PhaseTransitionCard from "@/components/chat/messages/PhaseTransitionCard";
import ResumeSessionCard from "@/components/chat/messages/ResumeSessionCard";
import WelcomeCard from "@/components/chat/messages/WelcomeCard";
import ComplianceDashboardPanel from "@/components/context-panel/ComplianceDashboardPanel";
import ContextPanel from "@/components/context-panel/ContextPanel";
import DraftViewerPanel from "@/components/context-panel/DraftViewerPanel";
import InterviewTrackerPanel from "@/components/context-panel/InterviewTrackerPanel";
import LearningsPanel from "@/components/context-panel/LearningsPanel";
import OperationsDashboardPanel from "@/components/context-panel/OperationsDashboardPanel";
import PanelTabs from "@/components/context-panel/PanelTabs";
import SubmissionReadinessPanel from "@/components/context-panel/SubmissionReadinessPanel";
import VersionHistoryPanel from "@/components/context-panel/VersionHistoryPanel";
import LeftRail from "@/components/left-rail/LeftRail";
import PhaseItem from "@/components/left-rail/PhaseItem";
import PhaseStepper from "@/components/left-rail/PhaseStepper";
import QuickActions from "@/components/left-rail/QuickActions";
import SessionMeta from "@/components/left-rail/SessionMeta";
import SubProgress from "@/components/left-rail/SubProgress";
import OnboardingExperience from "@/components/onboarding/OnboardingExperience";
import ThreadColumn from "@/components/threads/ThreadColumn";
import { useProposalStore } from "@/lib/store";
import { patchProposalStore, resetProposalStore } from "@/test/store-fixture";
import type { ChatMessage, ComplianceIssue } from "@/lib/types";

const failureIssue: ComplianceIssue = {
  id: "FMT-1",
  category: "formatting",
  name: "Margin size",
  description: "Margins do not match requirements.",
  severity: "failed",
};

describe("component coverage and failure/security behaviors", () => {
  beforeEach(() => {
    resetProposalStore();
  });

  it("ChatInput trims and submits only non-empty content", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<ChatInput onSend={onSend} />);

    const box = screen.getByPlaceholderText(/ask in plain language/i);
    await user.type(box, "  hello team  {enter}");
    expect(onSend).toHaveBeenCalledWith("hello team");
  });

  it("MainChat renders workspace shell", () => {
    render(<MainChat onAction={vi.fn()} />);
    expect(screen.getByText(/granite workspace/i)).toBeInTheDocument();
    expect(screen.getByText(/current thread/i)).toBeInTheDocument();
  });

  it("MessageThread renders text and escapes script tags", () => {
    const messages: ChatMessage[] = [
      { id: "m1", type: "text", role: "agent", content: "<script>alert(1)</script> safe" },
    ];
    render(<MessageThread messages={messages} onAction={vi.fn()} />);
    expect(screen.getByText(/safe/i)).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
  });

  it("MessageThread keeps welcome actions accessible after conversation starts", () => {
    const messages: ChatMessage[] = [
      { id: "w1", type: "welcome", role: "agent" },
      { id: "m2", type: "text", role: "agent", content: "Next step guidance" },
    ];
    render(<MessageThread messages={messages} onAction={vi.fn()} />);
    expect(screen.getByText(/welcome to granite/i)).toBeInTheDocument();
    expect(screen.getByText(/next step guidance/i)).toBeInTheDocument();
  });

  it("NextActionBanner dismisses safely", async () => {
    const user = userEvent.setup();
    render(<NextActionBanner text="Complete profile" />);
    await user.click(screen.getByLabelText(/dismiss/i));
    expect(screen.queryByText(/complete profile/i)).not.toBeInTheDocument();
  });

  it("SuggestedActionsBar renders phase actions", () => {
    render(<SuggestedActionsBar onAction={vi.fn()} />);
    expect(screen.getByRole("button", { name: /quick onboarding/i })).toBeInTheDocument();
  });

  it("WorkflowTransparencyDeck expands dashboard view", async () => {
    const user = userEvent.setup();
    render(<WorkflowTransparencyDeck onAction={vi.fn()} />);
    await user.click(screen.getByRole("button", { name: /open dashboard/i }));
    expect(screen.getByText(/transparent process view/i)).toBeInTheDocument();
  });

  it("ChallengeCard emits action choices", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(
      <ChallengeCard
        category="logic"
        intensity={2}
        question="Why now?"
        context="Reviewers expect timing rationale."
        onAction={onAction}
      />
    );
    await user.click(screen.getByRole("button", { name: /harder question/i }));
    expect(onAction).toHaveBeenCalledWith("harder");
  });

  it("ComplianceReportCard shows fix action for failures", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(
      <ComplianceReportCard
        passed={2}
        failed={[failureIssue]}
        warnings={[]}
        onAction={onAction}
      />
    );
    await user.click(screen.getByRole("button", { name: /fix in chat/i }));
    expect(onAction).toHaveBeenCalledWith("fix:FMT-1");
  });

  it("DraftReviewBlock supports approve flow", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(
      <DraftReviewBlock
        sectionName="abstract"
        version={1}
        wordCount={350}
        pageEstimate={1}
        patternsApplied={["Clear rationale"]}
        concernsAddressed={["Scope clarity"]}
        content="Draft text"
        onAction={onAction}
      />
    );
    await user.click(screen.getByRole("button", { name: /approve/i }));
    expect(onAction).toHaveBeenCalledWith("approve:abstract");
  });

  it("FileUploadCard exposes cloud and local actions", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(<FileUploadCard onAction={onAction} />);
    await user.click(screen.getByRole("button", { name: /google drive/i }));
    expect(onAction).toHaveBeenCalledWith("connect-gdrive");
  });

  it("InterviewQuestionBlock toggles examples", async () => {
    const user = userEvent.setup();
    render(
      <InterviewQuestionBlock
        section={1}
        questionNum={1}
        totalInSection={5}
        question="What is the problem?"
        example="Describe concrete gap."
      />
    );
    await user.click(screen.getByRole("button", { name: /show example/i }));
    expect(screen.getByText(/describe concrete gap/i)).toBeInTheDocument();
  });

  it("LearningSummaryCard renders funded/rejected summaries", () => {
    render(
      <LearningSummaryCard
        proposalName="2025 ISF"
        outcome="rejected"
        weaknesses={[
          {
            id: "W1",
            category: "aims",
            description: "Aims were broad.",
            quote: "too broad",
            prevention: "Narrow claims",
          },
        ]}
      />
    );
    expect(screen.getByText(/weaknesses found/i)).toBeInTheDocument();
  });

  it("PhaseTransitionCard links to next phase action", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(<PhaseTransitionCard fromPhase={2} toPhase={3} summary="Ready to continue." onAction={onAction} />);
    await user.click(screen.getByRole("button", { name: /continue to learn from past work/i }));
    expect(onAction).toHaveBeenCalledWith("go-phase:3");
  });

  it("ResumeSessionCard renders continuation actions", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(
      <ResumeSessionCard
        proposalTitle="Alpha"
        currentPhase={4}
        completedPhases={[1, 2, 3]}
        lastActive="Today"
        onAction={onAction}
      />
    );
    await user.click(screen.getByRole("button", { name: /continue where i left off/i }));
    expect(onAction).toHaveBeenCalledWith("continue");
  });

  it("WelcomeCard renders CTA options", () => {
    patchProposalStore({ researcherInfo: { ...useProposalStore.getState().researcherInfo, name: "Ada" } });
    render(<WelcomeCard onAction={vi.fn()} />);
    expect(screen.getByText(/welcome, ada/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /repeat onboarding/i })).toBeInTheDocument();
  });

  it("ComplianceDashboardPanel handles no-run state", () => {
    render(<ComplianceDashboardPanel onAction={vi.fn()} />);
    expect(screen.getByText(/compliance check will run/i)).toBeInTheDocument();
  });

  it("ContextPanel renders operations tab by default", () => {
    render(<ContextPanel onAction={vi.fn()} />);
    expect(screen.getByText(/operations dashboard/i)).toBeInTheDocument();
  });

  it("DraftViewerPanel shows empty state without drafts", () => {
    render(<DraftViewerPanel />);
    expect(screen.getByText(/your proposal will appear here/i)).toBeInTheDocument();
  });

  it("InterviewTrackerPanel handles pre-start state", () => {
    render(<InterviewTrackerPanel />);
    expect(screen.getByText(/the interview will gather information/i)).toBeInTheDocument();
  });

  it("LearningsPanel handles empty learnings set", () => {
    render(<LearningsPanel />);
    expect(screen.getByText(/no past proposals analyzed yet/i)).toBeInTheDocument();
  });

  it("OperationsDashboardPanel renders process overview", () => {
    render(<OperationsDashboardPanel />);
    expect(screen.getByText(/operations dashboard/i)).toBeInTheDocument();
    expect(screen.getByText(/ongoing processes/i)).toBeInTheDocument();
  });

  it("PanelTabs switches active tab in store", async () => {
    const user = userEvent.setup();
    render(<PanelTabs />);
    await user.click(screen.getByRole("button", { name: /draft/i }));
    expect(useProposalStore.getState().ui.activeContextTab).toBe("draft");
  });

  it("SubmissionReadinessPanel renders blockers and actions", () => {
    render(<SubmissionReadinessPanel onAction={vi.fn()} />);
    expect(screen.getByText(/submission readiness/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /view blockers/i })).toBeInTheDocument();
  });

  it("VersionHistoryPanel creates and restores a snapshot", async () => {
    const user = userEvent.setup();
    const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);
    const store = useProposalStore.getState();
    store.setPhase(3);
    store.captureWorkspaceSnapshot("Checkpoint A", "manual");
    store.setPhase(5);

    render(<VersionHistoryPanel />);
    await user.click(screen.getByRole("button", { name: /^restore$/i }));
    expect(useProposalStore.getState().session.currentPhase).toBe(3);

    confirmSpy.mockRestore();
  });

  it("LeftRail renders navigation and quick actions", () => {
    render(<LeftRail onPhaseClick={vi.fn()} onAction={vi.fn()} />);
    expect(screen.getByText(/isf personal research grant/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /open operations dashboard/i })).toBeInTheDocument();
  });

  it("PhaseItem renders status-specific state", () => {
    render(<PhaseItem phase={2} label="ISF Requirements" status="active" onClick={vi.fn()} />);
    expect(screen.getByText(/isf requirements/i)).toBeInTheDocument();
  });

  it("PhaseStepper renders all seven phases", () => {
    render(<PhaseStepper onPhaseClick={vi.fn()} />);
    expect(screen.getAllByRole("button").length).toBeGreaterThanOrEqual(7);
  });

  it("QuickActions dispatches selected action", async () => {
    const user = userEvent.setup();
    const onAction = vi.fn();
    render(<QuickActions onAction={onAction} />);
    await user.click(screen.getByRole("button", { name: /export my data/i }));
    expect(onAction).toHaveBeenCalledWith("export-data");
  });

  it("SessionMeta shows not-saved fallback", () => {
    render(<SessionMeta />);
    expect(screen.getByText(/not saved yet/i)).toBeInTheDocument();
  });

  it("SubProgress supports interview and draft branches", () => {
    const { rerender } = render(<SubProgress phase={4} />);
    expect(screen.getByText(/eligibility & background/i)).toBeInTheDocument();
    rerender(<SubProgress phase={5} />);
    expect(screen.getByText(/abstract/i)).toBeInTheDocument();
  });

  it("OnboardingExperience blocks continuation until required fields are set", async () => {
    const user = userEvent.setup();
    const onComplete = vi.fn();
    render(<OnboardingExperience onComplete={onComplete} />);

    const continueButton = screen.getByRole("button", { name: /continue/i });
    expect(continueButton).toBeDisabled();
    await user.type(screen.getByPlaceholderText(/your name/i), "Ada");
    expect(continueButton).toBeEnabled();
  });

  it("ThreadColumn supports search, rename, and delete actions", async () => {
    const user = userEvent.setup();
    const onSelectThread = vi.fn();
    const onRenameThread = vi.fn();
    const onDeleteThread = vi.fn();

    vi.spyOn(window, "prompt").mockReturnValue("Renamed");
    render(
      <ThreadColumn
        threads={[
          {
            id: "t1",
            title: "Hypothesis review",
            updatedAt: new Date().toISOString(),
            messageCount: 3,
            snippet: "Need stronger justification",
          },
        ]}
        archivedThreads={[]}
        activeThreadId={null}
        collapsed={false}
        onSelectThread={onSelectThread}
        onCreateThread={vi.fn()}
        onToggleCollapsed={vi.fn()}
        onRenameThread={onRenameThread}
        onDeleteThread={onDeleteThread}
        onRestoreThread={vi.fn()}
        onPermanentDelete={vi.fn()}
        onEmptyTrash={vi.fn()}
      />
    );

    await user.type(screen.getByPlaceholderText(/search threads/i), "hypothesis");
    await user.click(screen.getByRole("button", { name: /rename/i }));
    expect(onRenameThread).toHaveBeenCalledWith("t1", "Renamed");

    // Click delete — should open confirmation dialog, not call handler yet
    await user.click(screen.getByRole("button", { name: /delete thread/i }));
    expect(onDeleteThread).not.toHaveBeenCalled();
    expect(screen.getByText("Delete thread?")).toBeInTheDocument();

    // Confirm the deletion
    await user.click(screen.getByRole("button", { name: /^Delete$/i }));
    expect(onDeleteThread).toHaveBeenCalledWith("t1");

    fireEvent.click(screen.getByRole("button", { name: /hypothesis review/i }));
    expect(onSelectThread).toHaveBeenCalledWith("t1");
  });
});
