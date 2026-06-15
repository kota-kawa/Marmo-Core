import type { ChatMessage } from "./types";

interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ConversationContext {
  name?: string | null;
  affiliation?: string | null;
  sources?: Array<{
    id: string;
    label: string;
    filename: string;
  }>;
}

interface ChatApiError {
  error?: string;
}

interface StreamEvent {
  token?: string;
  error?: string;
}

function toConversationMessages(
  history: ChatMessage[],
  newUserContent: string
): ConversationMessage[] {
  const textHistory = history.filter(
    (message): message is Extract<ChatMessage, { type: "text" }> =>
      message.type === "text"
  );

  return [...textHistory, { type: "text", role: "user", content: newUserContent, id: "__pending__" }]
    .map((message) => {
      const role: ConversationMessage["role"] =
        message.role === "agent" ? "assistant" : "user";
      return {
        role,
        content: message.content.trim(),
      };
    })
    .filter((message) => message.content.length > 0);
}

function cleanContextPayload(context?: ConversationContext) {
  if (
    !context ||
    (!context.name?.trim() && !context.affiliation?.trim() && !(context.sources?.length))
  ) {
    return undefined;
  }
  return {
    name: context.name?.trim() || undefined,
    affiliation: context.affiliation?.trim() || undefined,
    sources:
      context.sources && context.sources.length > 0
        ? context.sources.map((source) => ({
            id: source.id,
            label: source.label,
            filename: source.filename,
          }))
        : undefined,
  };
}

export async function streamAssistantReply(
  history: ChatMessage[],
  newUserContent: string,
  context: ConversationContext | undefined,
  onToken: (token: string) => void,
  onDone: () => void,
  onError: (error: string) => void,
): Promise<void> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages: toConversationMessages(history, newUserContent),
      context: cleanContextPayload(context),
    }),
  });

  if (!response.ok) {
    try {
      const payload = (await response.json()) as ChatApiError;
      onError(payload.error ?? `Request failed with status ${response.status}.`);
    } catch {
      onError(`Request failed with status ${response.status}.`);
    }
    return;
  }

  if (!response.body) {
    onError("No response body received.");
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const data = line.slice(6).trim();
        if (data === "[DONE]") {
          onDone();
          return;
        }
        try {
          const parsed = JSON.parse(data) as StreamEvent;
          if (parsed.error) {
            onError(parsed.error);
            return;
          }
          if (parsed.token) {
            onToken(parsed.token);
          }
        } catch {
          // Skip unparseable lines
        }
      }
    }
    onDone();
  } catch (err) {
    onError(err instanceof Error ? err.message : "Stream read error.");
  }
}

export async function fetchAssistantReply(
  history: ChatMessage[],
  newUserContent: string,
  context?: ConversationContext
): Promise<string> {
  // Kept for backward compatibility — collects streamed tokens into a single string
  return new Promise<string>((resolve, reject) => {
    let accumulated = "";
    streamAssistantReply(
      history,
      newUserContent,
      context,
      (token) => { accumulated += token; },
      () => {
        if (!accumulated.trim()) {
          reject(new Error("Backend returned an empty assistant reply."));
        } else {
          resolve(accumulated.trim());
        }
      },
      (error) => { reject(new Error(error)); },
    ).catch(reject);
  });
}
