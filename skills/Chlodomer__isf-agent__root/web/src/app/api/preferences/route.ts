import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";

export async function GET() {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized." }, { status: 401 });
  }

  // Local-dev fallback user has no DB record
  if (session.user.id === "local-dev-admin") {
    return NextResponse.json({ chatPersistenceConsent: false });
  }

  const user = await prisma.user.findUnique({
    where: { id: session.user.id },
    select: { chatPersistenceConsent: true },
  });

  if (!user) {
    return NextResponse.json({ error: "User not found." }, { status: 404 });
  }

  return NextResponse.json({
    chatPersistenceConsent: user.chatPersistenceConsent,
  });
}

export async function PATCH(request: Request) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized." }, { status: 401 });
  }

  if (session.user.id === "local-dev-admin") {
    return NextResponse.json(
      { error: "Preferences are not available in local-dev mode." },
      { status: 400 }
    );
  }

  let body: { chatPersistenceConsent?: boolean };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON." }, { status: 400 });
  }

  if (typeof body.chatPersistenceConsent !== "boolean") {
    return NextResponse.json(
      { error: "chatPersistenceConsent must be a boolean." },
      { status: 400 }
    );
  }

  const updated = await prisma.user.update({
    where: { id: session.user.id },
    data: {
      chatPersistenceConsent: body.chatPersistenceConsent,
      chatConsentUpdatedAt: new Date(),
    },
    select: { chatPersistenceConsent: true },
  });

  await prisma.auditLog.create({
    data: {
      actorUserId: session.user.id,
      action: body.chatPersistenceConsent
        ? "consent_granted"
        : "consent_revoked",
      entityType: "User",
      entityId: session.user.id,
      meta: { field: "chatPersistenceConsent" },
    },
  });

  return NextResponse.json({
    chatPersistenceConsent: updated.chatPersistenceConsent,
  });
}
