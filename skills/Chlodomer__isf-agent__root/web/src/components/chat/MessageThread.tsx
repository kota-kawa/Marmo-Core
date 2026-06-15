"use client";

import { useEffect, useRef } from "react";
import type { ChatMessage } from "@/lib/types";
import ReactMarkdown from "react-markdown";
import ChallengeCard from "./messages/ChallengeCard";
import InterviewQuestionBlock from "./messages/InterviewQuestionBlock";
import DraftReviewBlock from "./messages/DraftReviewBlock";
import ComplianceReportCard from "./messages/ComplianceReportCard";
import LearningSummaryCard from "./messages/LearningSummaryCard";
import PhaseTransitionCard from "./messages/PhaseTransitionCard";
import WelcomeCard from "./messages/WelcomeCard";
import ResumeSessionCard from "./messages/ResumeSessionCard";
import FileUploadCard from "./messages/FileUploadCard";

interface MessageThreadProps {
  messages: ChatMessage[];
  onAction: (action: string) => void;
  isLoading?: boolean;
}

function TypingIndicator() {
  return (
    <div className="flex justify-start my-3">
      <div className="flex items-center gap-1 rounded-2xl rounded-bl-md bg-[#efe5d8] px-4 py-3">
        <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-[#b59472] [animation-delay:0ms]" />
        <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-[#b59472] [animation-delay:150ms]" />
        <span className="h-2.5 w-2.5 animate-bounce rounded-full bg-[#b59472] [animation-delay:300ms]" />
      </div>
    </div>
  );
}

function TextMessage({ message }: { message: Extract<ChatMessage, { type: "text" }> }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} my-3`}>
      <div
        className={`max-w-[88%] rounded-2xl px-4 py-3 text-base leading-relaxed ${
          isUser
            ? "rounded-br-md bg-[#8f6440] text-white"
            : "rounded-bl-md bg-[#f1e8db] text-[#3f342b]"
        }`}
      >
        <ReactMarkdown
          components={{
            p: ({ children }) => <p className="whitespace-pre-wrap">{children}</p>,
            strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
            em: ({ children }) => <em className="italic">{children}</em>,
            ul: ({ children }) => <ul className="list-disc pl-5 space-y-1">{children}</ul>,
            ol: ({ children }) => <ol className="list-decimal pl-5 space-y-1">{children}</ol>,
            li: ({ children }) => <li>{children}</li>,
          }}
        >
          {message.content}
        </ReactMarkdown>
      </div>
    </div>
  );
}

function renderMessage(message: ChatMessage, onAction: (action: string) => void) {
  switch (message.type) {
    case "text":
      return <TextMessage key={message.id} message={message} />;
    case "challenge":
      return <ChallengeCard key={message.id} {...message} onAction={onAction} />;
    case "interview_question":
      return <InterviewQuestionBlock key={message.id} {...message} onAction={onAction} />;
    case "draft_review":
      return <DraftReviewBlock key={message.id} {...message} onAction={onAction} />;
    case "compliance_report":
      return <ComplianceReportCard key={message.id} {...message} onAction={onAction} />;
    case "learning_summary":
      return <LearningSummaryCard key={message.id} {...message} onAction={onAction} />;
    case "phase_transition":
      return <PhaseTransitionCard key={message.id} {...message} onAction={onAction} />;
    case "welcome":
      return <WelcomeCard key={message.id} onAction={onAction} />;
    case "resume_session":
      return <ResumeSessionCard key={message.id} {...message} onAction={onAction} />;
    case "file_upload":
      return <FileUploadCard key={message.id} onAction={onAction} />;
    default:
      return null;
  }
}

export default function MessageThread({ messages, onAction, isLoading }: MessageThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const hasSubstantiveHistory = messages.some(
    (message) => message.type !== "welcome" && message.type !== "file_upload"
  );
  const shouldAutoScrollToBottom = hasSubstantiveHistory || Boolean(isLoading);
  const visibleMessages = messages;

  // Track the last message's content length to auto-scroll during streaming
  const lastMsg = visibleMessages[visibleMessages.length - 1];
  const lastContentLength =
    lastMsg?.type === "text" ? lastMsg.content.length : 0;

  useEffect(() => {
    if (!shouldAutoScrollToBottom) return;
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [isLoading, shouldAutoScrollToBottom, visibleMessages.length, lastContentLength]);

  return (
    <div className="flex-1 min-h-0 overflow-y-auto bg-gradient-to-b from-[#fdf9f3] via-[#faf4ec] to-[#f4ecdf] px-4 pb-4 pt-3">
      {visibleMessages.length === 0 && (
        <div className="flex h-full items-center justify-center text-base text-[#766554]">
          Starting your grant writing session...
        </div>
      )}
      {visibleMessages.map((msg) => renderMessage(msg, onAction))}
      {isLoading &&
        (() => {
          const last = visibleMessages[visibleMessages.length - 1];
          const streamingStarted =
            last?.type === "text" &&
            last.role === "agent" &&
            last.content.length > 0;
          return !streamingStarted ? <TypingIndicator /> : null;
        })()}
      <div ref={bottomRef} />
    </div>
  );
}
