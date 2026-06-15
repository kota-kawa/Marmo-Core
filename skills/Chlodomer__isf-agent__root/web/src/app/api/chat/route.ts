import { NextResponse } from "next/server";
import { auth } from "@/auth";

interface IncomingMessage {
  role: "user" | "assistant";
  content: string;
}

interface ChatRequestBody {
  messages?: IncomingMessage[];
  context?: {
    name?: string;
    affiliation?: string;
    sources?: Array<{
      id?: string;
      label?: string;
      filename?: string;
    }>;
  };
}

interface AnthropicErrorResponse {
  error?: {
    message?: string;
  };
}

interface AnthropicStreamEvent {
  type: string;
  delta?: { type?: string; text?: string };
  error?: { message?: string };
}

const SYSTEM_PROMPT = [
  "You are an expert assistant for ISF grant preparation.",
  "Respond in plain text only. Do not use Markdown symbols such as *, _, #, or backticks.",
  "Use a businesslike, neutral tone.",
  "Do not use praise, flattery, motivational language, or conversational fillers.",
  "Do not compliment the user's topic, approach, or background.",
  "Prioritize precision over speed.",
  "Do not draft full proposal sections (for example abstract/aims/methods) until critical details are collected and the user explicitly asks for a draft.",
  "If details are missing, ask focused follow-up questions and wait for answers before drafting.",
  "At the start of information gathering, briefly state that you will ask a few short questions to understand the idea.",
  "Ask exactly one question per message while gathering inputs. Do not bundle multiple questions in one reply.",
  "Proactively invite the user to upload key literature, prior proposals, or reviewer comments when those could improve accuracy.",
  "When literature is discussed or uploaded, ask for the user's stance in practical terms: what they agree with, what they disagree with, and why.",
  "Keep replies short and practical: 2-5 sentences by default.",
  "When source ids are available in context, cite them inline as [S1], [S2], etc.",
  "If the user needs options, provide at most 3 focused choices and recommend one.",
  "Ask at most one follow-up question when needed.",
].join(" ");

function buildContextPrompt(context?: ChatRequestBody["context"]): string {
  if (!context) return "";

  const name = typeof context.name === "string" ? context.name.trim() : "";
  const affiliation =
    typeof context.affiliation === "string" ? context.affiliation.trim() : "";

  const notes: string[] = [];
  if (name) {
    notes.push(
      `The researcher's name is ${name}. Address by name when helpful, while keeping a direct business tone.`
    );
  }
  if (affiliation) {
    notes.push(
      `Their departmental affiliation is ${affiliation}. Use this context when examples or framing are relevant.`
    );
  }

  const sourceLines = Array.isArray(context.sources)
    ? context.sources
        .map((source) => {
          const id = typeof source.id === "string" ? source.id.trim() : "";
          const label = typeof source.label === "string" ? source.label.trim() : "";
          const filename = typeof source.filename === "string" ? source.filename.trim() : "";
          if (!id || !label) return null;
          return `${id}: ${label}${filename ? ` (${filename})` : ""}`;
        })
        .filter((line): line is string => Boolean(line))
        .slice(0, 15)
    : [];

  if (sourceLines.length > 0) {
    notes.push(
      [
        "The user provided these sources for grounding:",
        ...sourceLines,
        "When a claim uses one of these sources, append its id in brackets like [S1].",
        "If no provided source supports a claim, state that clearly instead of inventing a citation.",
      ].join(" ")
    );
  }

  return notes.join(" ");
}

function isIncomingMessage(value: unknown): value is IncomingMessage {
  if (!value || typeof value !== "object") return false;

  const candidate = value as Partial<IncomingMessage>;
  return (
    (candidate.role === "user" || candidate.role === "assistant") &&
    typeof candidate.content === "string"
  );
}

export async function POST(request: Request) {
  const session = await auth();
  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized." }, { status: 401 });
  }

  const apiKey = process.env.ANTHROPIC_API_KEY?.trim();
  if (!apiKey) {
    return NextResponse.json(
      {
        error:
          "ANTHROPIC_API_KEY is not configured on the server. Add it to your environment variables.",
      },
      { status: 500 }
    );
  }

  let body: ChatRequestBody;
  try {
    body = (await request.json()) as ChatRequestBody;
  } catch {
    return NextResponse.json({ error: "Invalid JSON body." }, { status: 400 });
  }

  const rawMessages = Array.isArray(body.messages) ? body.messages : [];
  const messages = rawMessages.filter(isIncomingMessage).map((message) => ({
    role: message.role,
    content: message.content.trim(),
  }));

  if (messages.length === 0) {
    return NextResponse.json(
      { error: "At least one valid user/assistant message is required." },
      { status: 400 }
    );
  }

  const configuredModel = process.env.ANTHROPIC_MODEL
    ?.trim()
    .replace(/^['"]|['"]$/g, "");
  const model = configuredModel || "claude-sonnet-4-20250514";
  const contextPrompt = buildContextPrompt(body.context);
  const systemPrompt = contextPrompt ? `${SYSTEM_PROMPT} ${contextPrompt}` : SYSTEM_PROMPT;

  const upstream = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model,
      max_tokens: 4096,
      temperature: 0.4,
      system: systemPrompt,
      messages,
      stream: true,
    }),
  });

  if (!upstream.ok) {
    // Anthropic returns JSON errors even when stream: true was requested
    let errorMessage = `Anthropic request failed with status ${upstream.status}.`;
    try {
      const errorData = (await upstream.json()) as AnthropicErrorResponse;
      if (errorData.error?.message) {
        errorMessage = errorData.error.message;
      }
    } catch {
      // Use default error message
    }
    return NextResponse.json({ error: errorMessage }, { status: upstream.status });
  }

  if (!upstream.body) {
    return NextResponse.json(
      { error: "No response body from upstream." },
      { status: 502 }
    );
  }

  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  let buffer = "";

  const stream = new ReadableStream({
    async start(controller) {
      const reader = upstream.body!.getReader();
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
            if (data === "[DONE]") continue;

            try {
              const event = JSON.parse(data) as AnthropicStreamEvent;
              if (
                event.type === "content_block_delta" &&
                event.delta?.type === "text_delta" &&
                event.delta.text
              ) {
                controller.enqueue(
                  encoder.encode(`data: ${JSON.stringify({ token: event.delta.text })}\n\n`)
                );
              } else if (event.type === "message_stop") {
                controller.enqueue(encoder.encode("data: [DONE]\n\n"));
              } else if (event.type === "error") {
                controller.enqueue(
                  encoder.encode(
                    `data: ${JSON.stringify({ error: event.error?.message || "Stream error" })}\n\n`
                  )
                );
              }
            } catch {
              // Skip unparseable lines
            }
          }
        }
        // Ensure DONE is sent if not already
        controller.enqueue(encoder.encode("data: [DONE]\n\n"));
      } catch {
        controller.enqueue(
          encoder.encode(`data: ${JSON.stringify({ error: "Stream interrupted" })}\n\n`)
        );
      } finally {
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
