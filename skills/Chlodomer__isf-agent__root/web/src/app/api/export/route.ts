import { NextResponse } from "next/server";
import { auth } from "@/auth";
import { getUserWorkspaceExport } from "@/lib/user-data";

export async function GET() {
  const session = await auth();
  const userId = session?.user?.id;
  if (!userId) {
    return NextResponse.json({ error: "Unauthorized." }, { status: 401 });
  }

  const payload = await getUserWorkspaceExport(userId);
  return NextResponse.json({
    exportedAt: new Date().toISOString(),
    scope: "user-owned-data",
    ...payload,
  });
}
