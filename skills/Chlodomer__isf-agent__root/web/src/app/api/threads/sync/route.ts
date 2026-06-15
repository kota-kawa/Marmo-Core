import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";

interface SyncThread {
  clientThreadId: string;
  title: string;
  titleOrigin?: string;
  archivedAt?: string | null;
  messages: Array<{
    role: string;
    type: string;
    content?: string;
    payload?: unknown;
  }>;
}

interface SyncBody {
  threads: SyncThread[];
}

export async function POST(request: Request) {
  const session = await auth();
  if (!session?.user?.id || session.user.id === "local-dev-admin") {
    return NextResponse.json({ error: "Unauthorized." }, { status: 401 });
  }

  const user = await prisma.user.findUnique({
    where: { id: session.user.id },
    select: { chatPersistenceConsent: true, projects: { select: { id: true }, take: 1 } },
  });

  if (!user?.chatPersistenceConsent) {
    return NextResponse.json(
      { error: "Chat persistence not enabled." },
      { status: 403 }
    );
  }

  let body: SyncBody;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON." }, { status: 400 });
  }

  if (!Array.isArray(body.threads)) {
    return NextResponse.json(
      { error: "threads array is required." },
      { status: 400 }
    );
  }

  // Get or create project
  let projectId = user.projects[0]?.id;
  if (!projectId) {
    const project = await prisma.project.create({
      data: {
        ownerUserId: session.user.id,
        title: "Default Project",
      },
    });
    projectId = project.id;
  }

  const results: Array<{
    clientThreadId: string;
    serverThreadId: string;
    messageCount: number;
  }> = [];

  for (const threadData of body.threads) {
    if (!threadData.clientThreadId || !Array.isArray(threadData.messages)) {
      continue;
    }

    // Skip if thread already exists in DB
    const existing = await prisma.thread.findUnique({
      where: { id: threadData.clientThreadId },
      select: { id: true },
    });
    if (existing) {
      results.push({
        clientThreadId: threadData.clientThreadId,
        serverThreadId: existing.id,
        messageCount: 0,
      });
      continue;
    }

    const thread = await prisma.thread.create({
      data: {
        id: threadData.clientThreadId,
        projectId,
        title: threadData.title || "New thread",
        titleOrigin: threadData.titleOrigin || "auto",
        archivedAt: threadData.archivedAt ? new Date(threadData.archivedAt) : null,
        messages: {
          create: threadData.messages.map((msg) => ({
            role: msg.role,
            type: msg.type,
            content: msg.content ?? null,
            payload: msg.payload ? (msg.payload as object) : undefined,
          })),
        },
      },
    });

    results.push({
      clientThreadId: threadData.clientThreadId,
      serverThreadId: thread.id,
      messageCount: threadData.messages.length,
    });
  }

  return NextResponse.json({ synced: results });
}
