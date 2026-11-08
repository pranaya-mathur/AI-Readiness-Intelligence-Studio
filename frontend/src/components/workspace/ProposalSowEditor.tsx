"use client";

import React, { useState } from "react";
import type { ProposalSowPayload } from "./types";

interface Props {
  payload: ProposalSowPayload | null;
  busy?: boolean;
  message?: string;
  onGenerate: (feeEstimate: Record<string, unknown>) => Promise<void> | void;
  onExport: () => Promise<void> | void;
}

export default function ProposalSowEditor({
  payload,
  busy,
  message,
  onGenerate,
  onExport,
}: Props) {
  const fee = (payload?.fee_estimate || {}) as Record<string, unknown>;
  const [pilotFee, setPilotFee] = useState(String(fee.pilot_fee ?? ""));
  const [implementationFee, setImplementationFee] = useState(
    String(fee.implementation_fee ?? "")
  );
  const [currency, setCurrency] = useState(String(fee.currency ?? "USD"));
  const [assumptions, setAssumptions] = useState(
    Array.isArray(fee.assumptions) ? (fee.assumptions as string[]).join("\n") : ""
  );

  const proposal = payload?.proposal_package as Record<string, unknown> | null | undefined;
  const sow = payload?.sow_package;
  const commercial = proposal
    ? {
        client_benefit_model: proposal.client_benefit_model,
        proposed_project_fees: proposal.proposed_project_fees,
        operating_cost_estimates: proposal.operating_cost_estimates,
        missing_information: proposal.missing_information,
      }
    : null;

  return (
    <div className="space-y-4">
      <div className="glass-panel rounded-xl p-5 space-y-3">
        <h3 className="text-sm font-semibold text-slate-100">Proposal & SOW Draft</h3>
        <p className="text-[11px] text-slate-500">
          Fees are entered explicitly. Modeled client ROI is never used as the selling price.
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <label className="text-[11px] text-slate-400 space-y-1">
            Currency
            <input
              value={currency}
              onChange={(e) => setCurrency(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
            />
          </label>
          <label className="text-[11px] text-slate-400 space-y-1">
            Pilot fee
            <input
              value={pilotFee}
              onChange={(e) => setPilotFee(e.target.value)}
              placeholder="Required — incomplete if blank"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
            />
          </label>
          <label className="text-[11px] text-slate-400 space-y-1">
            Implementation fee
            <input
              value={implementationFee}
              onChange={(e) => setImplementationFee(e.target.value)}
              placeholder="Optional"
              className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
            />
          </label>
        </div>
        <label className="block text-[11px] text-slate-400 space-y-1">
          Fee assumptions (one per line)
          <textarea
            value={assumptions}
            onChange={(e) => setAssumptions(e.target.value)}
            rows={3}
            className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
          />
        </label>
        <div className="flex flex-wrap gap-2">
          <button
            disabled={busy}
            onClick={() =>
              onGenerate({
                currency,
                pilot_fee: pilotFee === "" ? null : Number(pilotFee),
                implementation_fee:
                  implementationFee === "" ? null : Number(implementationFee),
                assumptions: assumptions
                  .split("\n")
                  .map((s) => s.trim())
                  .filter(Boolean),
              })
            }
            className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-xs font-semibold text-white"
          >
            Generate draft
          </button>
          <button
            disabled={busy || !payload?.complete}
            onClick={() => onExport()}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-xs font-semibold text-slate-200"
          >
            Export proposal/SOW DOCX
          </button>
        </div>
        {message && <p className="text-[11px] text-amber-400">{message}</p>}
      </div>

      {commercial && (
        <div className="glass-panel rounded-xl p-5 space-y-2 text-xs text-slate-300">
          <h4 className="font-semibold text-slate-100">Commercial separation</h4>
          <pre className="whitespace-pre-wrap text-[11px] text-slate-400 overflow-auto max-h-48">
            {JSON.stringify(commercial, null, 2)}
          </pre>
        </div>
      )}

      {proposal && (
        <div className="glass-panel rounded-xl p-5 space-y-2 text-xs text-slate-300">
          <h4 className="font-semibold text-slate-100">Proposal package</h4>
          <pre className="whitespace-pre-wrap text-[11px] text-slate-400 overflow-auto max-h-72">
            {JSON.stringify(proposal, null, 2)}
          </pre>
        </div>
      )}

      {sow && (
        <div className="glass-panel rounded-xl p-5 space-y-2 text-xs text-slate-300">
          <h4 className="font-semibold text-slate-100">Statement of work</h4>
          <pre className="whitespace-pre-wrap text-[11px] text-slate-400 overflow-auto max-h-72">
            {JSON.stringify(sow, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
