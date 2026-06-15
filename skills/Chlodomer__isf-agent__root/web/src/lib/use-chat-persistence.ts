"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useProposalStore } from "./store";
import type { ChatMessage } from "./types";

const BANNER_DISMISSED_KEY = "isf.persistence.banner.dismissed";

async function saveMessageToServer(
  threadId: string,
  threadTitle: string,
  msg: ChatMessage
) {
  if (msg.type !== "text" || !("content" in msg)) return;
  try {
    await fetch("/api/threads", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        threadId,
        threadTitle,
        message: {
          role: msg.role === "agent" ? "assistant" : "user",
          type: msg.type,
          content: msg.content,
        },
      }),
    });
  } catch {
    // Fire-and-forget: persistence failure should not break the UX
  }
}

export function useChatPersistence(
  threadId: string | null,
  threadTitle: string
) {
  const consent = useProposalStore((s) => s.chatPersistenceConsent);
  const setConsent = useProposalStore((s) => s.setChatPersistenceConsent);
  const messages = useProposalStore((s) => s.messages);
  const savedCountRef = useRef(0);
  const prevThreadIdRef = useRef<string | null>(null);
  const [bannerDismissed, setBannerDismissed] = useState(() => {
    if (typeof window === "undefined") return true;
    try {
      return window.localStorage.getItem(BANNER_DISMISSED_KEY) === "true";
    } catch {
      return false;
    }
  });

  // Reset saved count when thread changes
  useEffect(() => {
    if (prevThreadIdRef.current !== threadId) {
      prevThreadIdRef.current = threadId;
      savedCountRef.current = 0;
    }
  }, [threadId]);

  // Load consent preference on mount
  useEffect(() => {
    async function loadConsent() {
      try {
        const res = await fetch("/api/preferences");
        if (res.ok) {
          const data = await res.json();
          setConsent(data.chatPersistenceConsent ?? false);
        } else {
          setConsent(false);
        }
      } catch {
        setConsent(false);
      }
    }
    loadConsent();
  }, [setConsent]);

  // Save new completed messages when consent is active
  useEffect(() => {
    if (!consent || !threadId) return;

    const newCount = messages.length;
    const prevCount = savedCountRef.current;
    if (newCount <= prevCount) return;

    const newMessages = messages.slice(prevCount);
    for (const msg of newMessages) {
      // Only save text messages that have actual content (skip streaming placeholders)
      if (msg.type === "text" && "content" in msg && msg.content.length > 0) {
        void saveMessageToServer(threadId, threadTitle, msg);
        savedCountRef.current = messages.indexOf(msg) + 1;
      }
    }
  }, [consent, messages, threadId, threadTitle]);

  const updateConsent = useCallback(
    async (newConsent: boolean) => {
      try {
        const res = await fetch("/api/preferences", {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ chatPersistenceConsent: newConsent }),
        });

        if (res.ok) {
          setConsent(newConsent);
          return true;
        }
      } catch {
        // Failed to update
      }
      return false;
    },
    [setConsent]
  );

  const dismissBanner = useCallback(() => {
    setBannerDismissed(true);
    try {
      window.localStorage.setItem(BANNER_DISMISSED_KEY, "true");
    } catch {
      // no-op
    }
  }, []);

  const showBanner = consent === false && !bannerDismissed;

  return { consent, updateConsent, showBanner, dismissBanner };
}
