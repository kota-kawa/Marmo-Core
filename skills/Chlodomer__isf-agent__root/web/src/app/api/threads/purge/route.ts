import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { prisma } from "@/lib/prisma";

export async function DELETE() {
  const session = await auth();
  if (!session?.user?.id || session.user.id === "local-dev-admin") {
    return NextResponse.json({ error: "Unauthorized." }, { status: 401 });
  }

  const projects = await prisma.project.findMany({
    where: { ownerUserId: session.user.id },
    select: { id: true },
  });

  const projectIds = projects.map((p) => p.id);

  if (projectIds.length === 0) {
    return NextResponse.json({ deleted: 0 });
  }

  // Threads cascade-delete their messages
  const deleted = await prisma.thread.deleteMany({
    where: { projectId: { in: projectIds } },
  });

  await prisma.auditLog.create({
    data: {
      actorUserId: session.user.id,
      action: "chat_data_purged",
      entityType: "User",
      entityId: session.user.id,
      meta: { threadsDeleted: deleted.count },
    },
  });

  return NextResponse.json({ deleted: deleted.count });
}
