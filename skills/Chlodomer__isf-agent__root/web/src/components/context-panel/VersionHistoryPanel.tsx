"use client";

import { Clock3, RotateCcw, Save } from "lucide-react";
import { useProposalStore } from "@/lib/store";
import { SECTION_ORDER } from "@/lib/types";

function formatRelative(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins} min ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

export default function VersionHistoryPanel() {
  const snapshots = useProposalStore((s) => s.versionHistory);
  const captureSnapshot = useProposalStore((s) => s.captureWorkspaceSnapshot);
  const restoreSnapshot = useProposalStore((s) => s.restoreWorkspaceSnapshot);
  const addMessage = useProposalStore((s) => s.addMessage);

  const onCreateSnapshot = () => {
    const snapshot = captureSnapshot("Manual restore point", "manual");
    addMessage({
      id: `snapshot-created-${snapshot.id}`,
      type: "text",
      role: "agent",
      content: `Created restore point at ${new Date(snapshot.createdAt).toLocaleString()}.`,
    });
  };

  const onRestoreSnapshot = (snapshotId: string, label: string) => {
    const shouldRestore = window.confirm(
      `Restore workspace to "${label}"? Current unsaved progress in this thread will be replaced.`
    );
    if (!shouldRestore) return;

    const restoreGuard = captureSnapshot(`Auto backup before restore: ${label}`, "auto");
    const restored = restoreSnapshot(snapshotId);

    if (!restored) {
      addMessage({
        id: `snapshot-restore-failed-${snapshotId}-${restoreGuard.id}`,
        type: "text",
        role: "agent",
        content: "Could not restore this snapshot. It may no longer exist.",
      });
      return;
    }

    addMessage({
      id: `snapshot-restored-${snapshotId}-${restoreGuard.id}`,
      type: "text",
      role: "agent",
      content: `Restored "${label}". Safety backup captured as "${restoreGuard.label}".`,
    });
  };

  if (snapshots.length === 0) {
    return (
      <div className="flex h-full flex-col">
        <div className="border-b border-slate-200 px-4 py-3">
          <h3 className="font-display text-sm text-slate-900">Version History</h3>
          <p className="mt-1 text-xs text-slate-500">Create restore points and return to them later.</p>
        </div>
        <div className="flex flex-1 flex-col items-center justify-center p-8 text-center">
          <p className="text-sm text-slate-500">
            No snapshots yet. Create your first restore point before major edits.
          </p>
          <button
            onClick={onCreateSnapshot}
            className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            <Save size={12} />
            Create restore point
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-slate-200 px-4 py-3">
        <div className="flex items-center justify-between gap-2">
          <div>
            <h3 className="font-display text-sm text-slate-900">Version History</h3>
            <p className="mt-1 text-xs text-slate-500">{snapshots.length} restore point(s) in this thread.</p>
          </div>
          <button
            onClick={onCreateSnapshot}
            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            <Save size={12} />
            Snapshot
          </button>
        </div>
      </div>

      <div className="flex-1 space-y-2 overflow-y-auto p-4">
        {snapshots.map((snapshot) => {
          const drafted = SECTION_ORDER.filter((section) =>
            Boolean(snapshot.state.proposalSections[section].draft)
          ).length;
          const approved = SECTION_ORDER.filter(
            (section) => snapshot.state.proposalSections[section].approved
          ).length;
          return (
            <div key={snapshot.id} className="rounded-xl border border-slate-200 bg-white p-3">
              <div className="mb-1 flex items-center justify-between gap-2">
                <p className="text-xs font-semibold text-slate-800">{snapshot.label}</p>
                <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-slate-600">
                  Phase {snapshot.phase}
                </span>
              </div>
              <p className="text-xs text-slate-500">
                {snapshot.reason === "manual" ? "Manual" : "Auto"} snapshot
              </p>
              <div className="mt-2 flex items-center gap-3 text-[11px] text-slate-500">
                <span className="inline-flex items-center gap-1">
                  <Clock3 size={11} />
                  {formatRelative(snapshot.createdAt)}
                </span>
                <span>{drafted}/{SECTION_ORDER.length} drafted</span>
                <span>{approved}/{SECTION_ORDER.length} approved</span>
              </div>
              <button
                onClick={() => onRestoreSnapshot(snapshot.id, snapshot.label)}
                className="mt-3 inline-flex items-center gap-1.5 rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
              >
                <RotateCcw size={11} />
                Restore
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
