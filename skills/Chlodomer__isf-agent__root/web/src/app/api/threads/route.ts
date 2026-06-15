import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";

interface SaveMessageBody {
  threadId: string;
  threadTitle?: string;
  message: {
    id?: string;
    role: string;
    type: string;
    content?: string;
    payload?: unknown;
  };
}

export async function POST(request: Request) {
  const session = await auth();
  if (!session?.user?.id || session.user.id === "local-dev-admin") {
    return NextResponse.json({ error: "Unauthorized." }, { status: 401 });
  }

  // Check consent
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

  let body: SaveMessageBody;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON." }, { status: 400 });
  }

  if (!body.threadId || !body.message?.role || !body.message?.type) {
    return NextResponse.json(
      { error: "threadId, message.role, and message.type are required." },
      { status: 400 }
    );
  }

  // Get or create project for user
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

  // Upsert thread
  const existingThread = await prisma.thread.findUnique({
    where: { id: body.threadId },
    select: { id: true, projectId: true },
  });

  let threadId: string;
  if (existingThread) {
    // Verify thread belongs to user's project
    const project = await prisma.project.findFirst({
      where: { id: existingThread.projectId, ownerUserId: session.user.id },
      select: { id: true },
    });
    if (!project) {
      return NextResponse.json({ error: "Thread not found." }, { status: 404 });
    }
    threadId = existingThread.id;
  } else {
    const thread = await prisma.thread.create({
      data: {
        id: body.threadId,
        projectId,
        title: body.threadTitle ?? "New thread",
      },
    });
    threadId = thread.id;
  }

  // Create message
  const message = await prisma.message.create({
    data: {
      threadId,
      role: body.message.role,
      type: body.message.type,
      content: body.message.content ?? null,
      payload: body.message.payload
        ? (body.message.payload as object)
        : undefined,
    },
  });

  return NextResponse.json({ threadId, messageId: message.id });
}
