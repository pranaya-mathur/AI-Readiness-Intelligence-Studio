"use client";

import React from "react";
import type { PortfolioItem } from "./types";

interface Props {
  items: PortfolioItem[];
  businessUnitFilter: string;
  onBusinessUnitFilter: (value: string) => void;
  onOpenAssessment: (id: number) => void;
}

export default function EnterprisePortfolio({
  items,
  businessUnitFilter,
  onBusinessUnitFilter,
  onOpenAssessment,
}: Props) {
  const units = Array.from(
    new Set(items.map((i) => i.business_unit).filter(Boolean) as string[])
  ).sort();
  const filtered = businessUnitFilter
    ? items.filter((i) => (i.business_unit || "") === businessUnitFilter)
    : items;

  return (
    <div className="glass-panel rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">Enterprise AI Portfolio</h3>
          <p className="text-[11px] text-slate-500 mt-1">
            Per-assessment opportunities and decisions. Portfolio totals do not sum overlapping ROI.
          </p>
        </div>
        <select
          value={businessUnitFilter}
          onChange={(e) => onBusinessUnitFilter(e.target.value)}
          className="bg-slate-950 border border-slate-800 text-xs rounded-lg px-3 py-1.5 text-slate-300"
        >
          <option value="">All business units</option>
          {units.map((u) => (
            <option key={u} value={u}>
              {u}
            </option>
          ))}
        </select>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="text-slate-500 border-b border-slate-800">
            <tr>
              <th className="py-2 pr-3 font-medium">Assessment</th>
              <th className="py-2 pr-3 font-medium">Business unit</th>
              <th className="py-2 pr-3 font-medium">Workflow</th>
              <th className="py-2 pr-3 font-medium">Investment</th>
              <th className="py-2 pr-3 font-medium">Pilot priority</th>
              <th className="py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((item) => (
              <tr key={item.assessment_id} className="border-b border-slate-900/80 text-slate-300">
                <td className="py-2.5 pr-3">
                  <div className="font-medium text-slate-200">{item.company_name}</div>
                  <div className="text-[10px] text-slate-500">
                    Score {item.overall_score != null ? `${item.overall_score}/100` : "—"}
                  </div>
                </td>
                <td className="py-2.5 pr-3">{item.business_unit || "—"}</td>
                <td className="py-2.5 pr-3">{item.workflow_status || item.status || "—"}</td>
                <td className="py-2.5 pr-3">{item.investment_decision_status || "pending"}</td>
                <td className="py-2.5 pr-3">{item.recommended_first_pilot || "—"}</td>
                <td className="py-2.5">
                  <button
                    onClick={() => onOpenAssessment(item.assessment_id)}
                    className="text-blue-400 hover:text-blue-300 font-semibold"
                  >
                    Open
                  </button>
                </td>
              </tr>
            ))}
            {!filtered.length && (
              <tr>
                <td colSpan={6} className="py-6 text-center text-slate-500">
                  No assessments in this portfolio yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
