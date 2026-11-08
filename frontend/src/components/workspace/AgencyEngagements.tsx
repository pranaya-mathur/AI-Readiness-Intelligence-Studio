"use client";

import React from "react";
import type { EngagementItem } from "./types";

interface Props {
  engagements: EngagementItem[];
  onOpenClient: (clientId: number) => void;
  onCreateEngagement?: () => void;
}

export default function AgencyEngagements({
  engagements,
  onOpenClient,
  onCreateEngagement,
}: Props) {
  return (
    <div className="glass-panel rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">Client Engagements</h3>
          <p className="text-[11px] text-slate-500 mt-1">
            Isolated client workspaces for discovery through proposal handoff.
          </p>
        </div>
        {onCreateEngagement && (
          <button
            onClick={onCreateEngagement}
            className="text-xs px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold"
          >
            New engagement
          </button>
        )}
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        {engagements.map((eng) => (
          <button
            key={eng.client_id}
            onClick={() => onOpenClient(eng.client_id)}
            className="text-left border border-slate-800 hover:border-slate-700 rounded-xl p-4 bg-slate-950/50 transition-colors"
          >
            <div className="flex items-start justify-between gap-2">
              <div>
                <div className="text-sm font-semibold text-slate-100">{eng.name}</div>
                <div className="text-[11px] text-slate-500 mt-0.5">
                  {eng.industry || "Industry TBD"} · {eng.business_unit || "No BU"}
                </div>
              </div>
              <span className="text-[10px] px-2 py-0.5 rounded-full border border-slate-700 text-slate-400">
                {eng.engagement_status || "draft"}
              </span>
            </div>
            <div className="mt-3 text-[11px] text-slate-400 flex gap-3">
              <span>Proposal {eng.has_proposal ? "ready" : "incomplete"}</span>
              <span>SOW {eng.has_sow ? "ready" : "incomplete"}</span>
            </div>
            {eng.consultant_notes && (
              <p className="mt-2 text-[11px] text-slate-500 line-clamp-2">{eng.consultant_notes}</p>
            )}
          </button>
        ))}
        {!engagements.length && (
          <div className="text-xs text-slate-500 col-span-2 py-6 text-center border border-dashed border-slate-800 rounded-xl">
            No client engagements yet. Create a client to start discovery.
          </div>
        )}
      </div>
    </div>
  );
}
