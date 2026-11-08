"use client";

import React, { useMemo, useState } from "react";

export interface WorkspaceMember {
  membership_id: number;
  user_id: number;
  email: string;
  full_name?: string | null;
  role: string;
  authorized_client_ids?: number[] | null;
}

export interface MemberClientOption {
  id: number;
  name: string;
}

interface Props {
  members: WorkspaceMember[];
  clients: MemberClientOption[];
  canManage: boolean;
  busy?: boolean;
  message?: string;
  onRefresh: () => void;
  onAddMember: (payload: {
    email: string;
    role: string;
    full_name?: string;
    temporary_password?: string;
    authorized_client_ids?: number[];
  }) => Promise<void> | void;
  onUpdateMember: (
    userId: number,
    payload: { role: string; authorized_client_ids?: number[] | null }
  ) => Promise<void> | void;
}

const ROLES = [
  { value: "owner_admin", label: "Owner / Admin" },
  { value: "consultant_analyst", label: "Consultant / Analyst" },
  { value: "reviewer_approver", label: "Reviewer / Approver" },
  { value: "client_viewer", label: "Client / Viewer" },
] as const;

function roleLabel(role: string) {
  return ROLES.find((r) => r.value === role)?.label || role;
}

export default function MemberAccessPanel({
  members,
  clients,
  canManage,
  busy,
  message,
  onRefresh,
  onAddMember,
  onUpdateMember,
}: Props) {
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<string>("consultant_analyst");
  const [password, setPassword] = useState("");
  const [selectedClientIds, setSelectedClientIds] = useState<number[]>([]);
  const [editingUserId, setEditingUserId] = useState<number | null>(null);
  const [editRole, setEditRole] = useState("consultant_analyst");
  const [editClientIds, setEditClientIds] = useState<number[]>([]);

  const clientNameById = useMemo(() => {
    const map = new Map<number, string>();
    clients.forEach((c) => map.set(c.id, c.name));
    return map;
  }, [clients]);

  const toggleClient = (id: number, list: number[], setter: (next: number[]) => void) => {
    setter(list.includes(id) ? list.filter((x) => x !== id) : [...list, id]);
  };

  const submitAdd = async () => {
    if (!email.trim()) return;
    await onAddMember({
      email: email.trim(),
      role,
      full_name: fullName.trim() || undefined,
      temporary_password: password || undefined,
      authorized_client_ids: role === "client_viewer" ? selectedClientIds : undefined,
    });
    setEmail("");
    setFullName("");
    setPassword("");
    setSelectedClientIds([]);
    setRole("consultant_analyst");
  };

  return (
    <div className="glass-panel rounded-xl p-5 space-y-4">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">Workspace members & access</h3>
          <p className="text-[11px] text-slate-500 mt-1">
            Client viewers must be scoped to explicit engagements. Internal roles keep organization-wide access.
          </p>
        </div>
        <button
          onClick={onRefresh}
          disabled={busy}
          className="text-xs px-3 py-1.5 rounded-lg border border-slate-700 text-slate-300 hover:bg-slate-900 disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="text-slate-500 border-b border-slate-800">
            <tr>
              <th className="py-2 pr-3 font-medium">Member</th>
              <th className="py-2 pr-3 font-medium">Role</th>
              <th className="py-2 pr-3 font-medium">Authorized clients</th>
              <th className="py-2 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            {members.map((m) => (
              <tr key={m.membership_id} className="border-b border-slate-900/80 text-slate-300">
                <td className="py-2.5 pr-3">
                  <div className="font-medium text-slate-200">{m.full_name || m.email}</div>
                  <div className="text-[10px] text-slate-500">{m.email}</div>
                </td>
                <td className="py-2.5 pr-3">
                  {editingUserId === m.user_id ? (
                    <select
                      value={editRole}
                      onChange={(e) => setEditRole(e.target.value)}
                      className="bg-slate-950 border border-slate-800 rounded-lg px-2 py-1 text-xs"
                    >
                      {ROLES.map((r) => (
                        <option key={r.value} value={r.value}>
                          {r.label}
                        </option>
                      ))}
                    </select>
                  ) : (
                    roleLabel(m.role)
                  )}
                </td>
                <td className="py-2.5 pr-3">
                  {editingUserId === m.user_id && editRole === "client_viewer" ? (
                    <div className="flex flex-wrap gap-2 max-w-xs">
                      {clients.map((c) => (
                        <label key={c.id} className="inline-flex items-center gap-1 text-[10px]">
                          <input
                            type="checkbox"
                            checked={editClientIds.includes(c.id)}
                            onChange={() =>
                              toggleClient(c.id, editClientIds, setEditClientIds)
                            }
                          />
                          {c.name}
                        </label>
                      ))}
                      {!clients.length && (
                        <span className="text-slate-500">Create a client engagement first</span>
                      )}
                    </div>
                  ) : m.role === "client_viewer" ? (
                    <span>
                      {(m.authorized_client_ids || [])
                        .map((id) => clientNameById.get(id) || `#${id}`)
                        .join(", ") || "None assigned"}
                    </span>
                  ) : (
                    <span className="text-slate-500">Organization-wide</span>
                  )}
                </td>
                <td className="py-2.5">
                  {canManage && (
                    editingUserId === m.user_id ? (
                      <div className="flex gap-2">
                        <button
                          disabled={busy || (editRole === "client_viewer" && !editClientIds.length)}
                          onClick={async () => {
                            await onUpdateMember(m.user_id, {
                              role: editRole,
                              authorized_client_ids:
                                editRole === "client_viewer" ? editClientIds : null,
                            });
                            setEditingUserId(null);
                          }}
                          className="text-emerald-400 hover:text-emerald-300 font-semibold disabled:opacity-40"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingUserId(null)}
                          className="text-slate-500 hover:text-slate-300"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => {
                          setEditingUserId(m.user_id);
                          setEditRole(m.role);
                          setEditClientIds([...(m.authorized_client_ids || [])]);
                        }}
                        className="text-blue-400 hover:text-blue-300 font-semibold"
                      >
                        Edit
                      </button>
                    )
                  )}
                </td>
              </tr>
            ))}
            {!members.length && (
              <tr>
                <td colSpan={4} className="py-6 text-center text-slate-500">
                  No members loaded yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {canManage && (
        <div className="border border-slate-800 rounded-xl p-4 space-y-3">
          <h4 className="text-xs font-semibold text-slate-200">Add member</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <label className="text-[11px] text-slate-400 space-y-1">
              Email
              <input
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
                placeholder="user@client.example"
              />
            </label>
            <label className="text-[11px] text-slate-400 space-y-1">
              Full name
              <input
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
              />
            </label>
            <label className="text-[11px] text-slate-400 space-y-1">
              Role
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
              >
                {ROLES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-[11px] text-slate-400 space-y-1">
              Temporary password (new accounts)
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200"
                placeholder="Min 8 characters"
              />
            </label>
          </div>
          {role === "client_viewer" && (
            <div className="space-y-2">
              <div className="text-[11px] text-slate-400">
                Authorized client engagements (required)
              </div>
              <div className="flex flex-wrap gap-3">
                {clients.map((c) => (
                  <label key={c.id} className="inline-flex items-center gap-1.5 text-[11px] text-slate-300">
                    <input
                      type="checkbox"
                      checked={selectedClientIds.includes(c.id)}
                      onChange={() =>
                        toggleClient(c.id, selectedClientIds, setSelectedClientIds)
                      }
                    />
                    {c.name}
                  </label>
                ))}
                {!clients.length && (
                  <span className="text-[11px] text-amber-400">
                    No client engagements available. Create one before inviting a client viewer.
                  </span>
                )}
              </div>
            </div>
          )}
          <button
            disabled={
              busy ||
              !email.trim() ||
              (role === "client_viewer" && selectedClientIds.length === 0)
            }
            onClick={submitAdd}
            className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-xs font-semibold text-white"
          >
            Add member
          </button>
        </div>
      )}

      {message && <p className="text-[11px] text-amber-400">{message}</p>}
    </div>
  );
}
