"use client";

import { useCallback, useRef, useState } from "react";
import Image from "next/image";
import { FileText } from "lucide-react";
import { useProposalStore } from "@/lib/store";
import { getNextActionText } from "@/lib/chat-actions";
import { buildLocalAgentReply } from "@/lib/local-agent";
import { streamAssistantReply } from "@/lib/chat-backend";
import { INTERVIEW_SECTIONS, type ReferenceSource } from "@/lib/types";
import NextActionBanner from "./NextActionBanner";
import MessageThread from "./MessageThread";
import SuggestedActionsBar from "./SuggestedActionsBar";
import ChatInput from "./ChatInput";
import ChatPersistenceBanner from "./ChatPersistenceBanner";
import WorkflowTransparencyDeck from "./WorkflowTransparencyDeck";

interface MainChatProps {
  onAction: (action: string) => void;
  onAssistantReply?: (userPrompt: string, assistantReply: string) => void;
  activeThreadTitle?: string;
  activeThreadRecap?: string | null;
  showPersistenceBanner?: boolean;
  onAcceptPersistence?: () => void;
  onDismissPersistence?: () => void;
}

export default function MainChat({
  onAction,
  onAssistantReply,
  activeThreadTitle = "Current thread",
  activeThreadRecap = null,
  showPersistenceBanner = false,
  onAcceptPersistence,
  onDismissPersistence,
}: MainChatProps) {
  const messages = useProposalStore((s) => s.messages);
  const phase = useProposalStore((s) => s.session.currentPhase);
  const projectTitle = useProposalStore((s) => s.projectInfo.title);
  const interview = useProposalStore((s) => s.interview);
  const researcherInfo = useProposalStore((s) => s.researcherInfo);
  const referenceSources = useProposalStore((s) => s.referenceSources);
  const addReferenceSources = useProposalStore((s) => s.addReferenceSources);
  const addMessage = useProposalStore((s) => s.addMessage);
  const updateMessage = useProposalStore((s) => s.updateMessage);
  const [isSending, setIsSending] = useState(false);
  const accumulatedRef = useRef("");

  // Compute next action text
  const interviewProgress = interview.currentSection
    ? (() => {
        const section = INTERVIEW_SECTIONS.find((s) => s.id === interview.currentSection);
        const answered = interview.currentQuestion ? interview.currentQuestion - 1 : 0;
        return section
          ? {
              remaining: section.totalQuestions - answered,
              sectionLabel: section.label,
            }
          : undefined;
      })()
    : undefined;

  const nextActionText = getNextActionText(phase, interviewProgress);

  const registerUploadedSources = useCallback(
    (files: FileList) => {
      const existingCount = referenceSources.length;
      const newSources: ReferenceSource[] = Array.from(files).map((file, index) => ({
        id: `S${existingCount + index + 1}`,
        label: file.name.replace(/\.[^.]+$/, ""),
        filename: file.name,
        mimeType: file.type || "application/octet-stream",
        size: file.size,
        addedAt: new Date().toISOString(),
      }));

      addReferenceSources(newSources);

      const uploadSummary = newSources
        .map((source) => `${source.id}: ${source.filename}`)
        .join("\n");

      addMessage({
        id: `source-upload-${Date.now()}`,
        type: "text",
        role: "agent",
        content: [
          `Added ${newSources.length} source file(s) for grounded drafting.`,
          uploadSummary,
          "I will cite these in responses using bracket IDs like [S1].",
        ].join("\n"),
      });
    },
    [addMessage, addReferenceSources, referenceSources.length]
  );

  const handleSend = (content: string) => {
    if (isSending) return;

    const normalized = content.trim().toLowerCase();
    if (
      normalized === "/validate" ||
      normalized === "/fix" ||
      normalized === "/checklist" ||
      normalized === "/readiness" ||
      normalized === "/sources" ||
      normalized === "/approve" ||
      normalized === "/preview" ||
      normalized === "/requirements"
    ) {
      onAction(normalized);
      return;
    }

    addMessage({
      id: `msg-${Date.now()}`,
      type: "text",
      role: "user",
      content,
    });

    const localReply = buildLocalAgentReply(content, {
      name: researcherInfo.name,
      affiliation: researcherInfo.department,
    });
    if (localReply) {
      addMessage(localReply);
      return;
    }

    setIsSending(true);
    const assistantMsgId = `msg-${Date.now()}-assistant`;
    accumulatedRef.current = "";

    addMessage({
      id: assistantMsgId,
      type: "text",
      role: "agent",
      content: "",
    });

    let rafPending = false;

    void streamAssistantReply(
      messages,
      content,
      {
        name: researcherInfo.name,
        affiliation: researcherInfo.department,
        sources: referenceSources.map((source) => ({
          id: source.id,
          label: source.label,
          filename: source.filename,
        })),
      },
      (token) => {
        accumulatedRef.current += token;
        if (!rafPending) {
          rafPending = true;
          requestAnimationFrame(() => {
            rafPending = false;
            updateMessage(assistantMsgId, accumulatedRef.current);
          });
        }
      },
      () => {
        // Flush any remaining tokens
        updateMessage(assistantMsgId, accumulatedRef.current);
        if (accumulatedRef.current.trim().length > 0) {
          onAssistantReply?.(content, accumulatedRef.current);
        }
        setIsSending(false);
      },
      (error) => {
        if (accumulatedRef.current.length === 0) {
          updateMessage(assistantMsgId, `I couldn't complete the request: ${error}`);
        }
        setIsSending(false);
      },
    );
  };

  return (
    <div className="flex-1 flex flex-col min-w-0 min-h-[45vh] lg:min-h-0 h-full rounded-2xl border border-[#ddcfbf]/90 bg-gradient-to-b from-white/90 via-[#faf5ee]/88 to-[#f4ecdf]/84 backdrop-blur-sm shadow-[0_24px_48px_-32px_rgba(47,41,36,0.42)]">
      <div className="mx-4 mt-4 rounded-xl border border-[#d8c8b3] bg-gradient-to-r from-[#fff7ec] via-[#f6ede0] to-[#ede4d8] px-4 py-3.5">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <Image
              src="/granite-logo.png"
              alt="Granite logo"
              width={44}
              height={44}
              className="h-11 w-11 flex-shrink-0 rounded-xl object-cover shadow-[0_10px_24px_-16px_rgba(47,41,36,0.65)]"
            />
            <div className="min-w-0">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#7a644e]">
                Granite Workspace
              </p>
              <h2 className="font-display truncate text-lg font-semibold text-[#2f2924]">
                {projectTitle || "New Proposal"}
              </h2>
            </div>
          </div>
          <span className="rounded-full border border-[#cab7a0] bg-white/80 px-2.5 py-1 text-xs font-medium text-[#6a5642]">
            Phase {phase}
          </span>
        </div>
        <p className="mt-2 truncate text-sm text-[#695848]">Current thread: {activeThreadTitle}</p>
      </div>
      {activeThreadRecap && (
        <div className="mx-4 mt-3 rounded-xl border border-[#d6c7b2] bg-[#f8f1e6] px-4 py-3">
          <div className="flex items-center gap-2 text-[#6a5540]">
            <FileText size={16} />
            <p className="text-sm font-semibold">{activeThreadTitle} recap</p>
          </div>
          <p className="mt-2 text-sm leading-relaxed text-[#5b4c3e]">{activeThreadRecap}</p>
        </div>
      )}
      <WorkflowTransparencyDeck onAction={onAction} />
      <NextActionBanner text={nextActionText} />
      <MessageThread messages={messages} onAction={onAction} isLoading={isSending} />
      <SuggestedActionsBar onAction={onAction} />
      {showPersistenceBanner && onAcceptPersistence && onDismissPersistence && (
        <ChatPersistenceBanner
          onAccept={onAcceptPersistence}
          onDismiss={onDismissPersistence}
        />
      )}
      <ChatInput onSend={handleSend} onFileUpload={registerUploadedSources} disabled={isSending} />
    </div>
  );
}
