"use client";

import React from "react";

const WORKFLOW_OPTIONS = [
  "draft",
  "discovery",
  "assessment_completed",
  "consultant_review",
  "investment_review",
  "approved",
  "proposal_prepared",
  "delivered",
] as const;

interface Props {
  workflowStatus?: string | null;
  approvalStatus?: string | null;
  investmentStatus?: string | null;
  locked?: boolean;
  busy?: boolean;
  onWorkflowChange: (status: string, reason: string) => Promise<void> | void;
}

export default function ReviewApprovalPanel({
  workflowStatus,
  approvalStatus,
  investmentStatus,
  locked,
  busy,
  onWorkflowChange,
}: Props) {
  const [status, setStatus] = React.useState(workflowStatus || "draft");
  const [reason, setReason] = React.useState("");

  React.useEffect(() => {
    setStatus(workflowStatus || "draft");
  }, [workflowStatus]);

  return (
    <div className="glass-panel rounded-xl p-5 space-y-3">
      <h3 className="text-sm font-semibold text-slate-100">Review & workflow</h3>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-[11px]">
        <div className="border border-slate-800 rounded-lg p-3">
          <div className="text-slate-500 uppercase tracking-wide">Assessment approval</div>
          <div className="text-slate-200 mt-1 font-semibold">{approvalStatus || "draft"}</div>
        </div>
        <div className="border border-slate-800 rounded-lg p-3">
          <div className="text-slate-500 uppercase tracking-wide">Investment decision</div>
          <div className="text-slate-200 mt-1 font-semibold">{investmentStatus || "pending"}</div>
        </div>
        <div className="border border-slate-800 rounded-lg p-3">
          <div className="text-slate-500 uppercase tracking-wide">Delivery lock</div>
          <div className="text-slate-200 mt-1 font-semibold">{locked ? "Locked" : "Editable"}</div>
        </div>
      </div>
      <div className="flex flex-col md:flex-row gap-2 md:items-end">
        <label className="text-[11px] text-slate-400 space-y-1 flex-1">
          Workspace workflow status
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
          >
            {WORKFLOW_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </label>
        <label className="text-[11px] text-slate-400 space-y-1 flex-[2]">
          Reason (required to reopen locked deliverables)
          <input
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
            placeholder="Audit reason"
          />
        </label>
        <button
          disabled={busy}
          onClick={() => onWorkflowChange(status, reason)}
          className="px-3 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 text-xs font-semibold text-white"
        >
          Update workflow
        </button>
      </div>
      <p className="text-[10px] text-slate-500">
        Assessment approval and investment approval remain distinct gates.
      </p>
    </div>
  );
}
