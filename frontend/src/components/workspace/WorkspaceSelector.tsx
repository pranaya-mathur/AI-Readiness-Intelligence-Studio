"use client";

import React from "react";
import type { WorkspaceSummary } from "./types";

interface Props {
  workspaces: WorkspaceSummary[];
  selectedId: number | null;
  onSelect: (workspace: WorkspaceSummary) => void;
}

export default function WorkspaceSelector({ workspaces, selectedId, onSelect }: Props) {
  if (!workspaces.length) {
    return (
      <div className="text-[10px] text-slate-500 border border-slate-800 rounded-lg px-3 py-1.5">
        No workspace
      </div>
    );
  }

  return (
    <select
      value={selectedId ?? workspaces[0].id}
      onChange={(e) => {
        const next = workspaces.find((w) => w.id === Number(e.target.value));
        if (next) onSelect(next);
      }}
      className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-3 py-1.5 max-w-[220px]"
      title="Workspace"
    >
      {workspaces.map((w) => (
        <option key={w.id} value={w.id}>
          {w.workspace_type === "enterprise" ? "Enterprise" : "Agency"} · {w.name}
        </option>
      ))}
    </select>
  );
}
