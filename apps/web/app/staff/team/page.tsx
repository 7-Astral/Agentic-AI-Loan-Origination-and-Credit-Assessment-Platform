"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";
import { useStaff } from "@/lib/staff-context";
import { api, type UserOut, ApiError } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { Card, CardHeader } from "@/components/ui/Card";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Field, Input, Select } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { IconLock, IconPencil, IconUserPlus, IconUsers } from "@/components/icons";

function initials(name: string) {
  return name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
}

export default function StaffTeam() {
  const { token, user: currentUser } = useAuth();
  const { position, positions, loading: staffLoading } = useStaff();
  const { show } = useToast();
  const [team, setTeam] = useState<UserOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ full_name: "", email: "", password: "", position_id: "" });
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [editUser, setEditUser] = useState<UserOut | null>(null);
  const [editForm, setEditForm] = useState({ full_name: "", position_id: "" });
  const [editError, setEditError] = useState<string | null>(null);
  const [editSubmitting, setEditSubmitting] = useState(false);

  useEffect(() => {
    if (!token) return;
    api
      .bankStaff(token)
      .then(setTeam)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [token]);

  useEffect(() => {
    setForm((f) => (f.position_id ? f : { ...f, position_id: positions[0]?.id || "" }));
  }, [positions]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setFormError(null);
    setSubmitting(true);
    try {
      const newStaff = await api.createBankStaff(token, form);
      setTeam((t) => [...t, newStaff]);
      setModalOpen(false);
      setForm({ full_name: "", email: "", password: "", position_id: positions[0]?.id || "" });
      show(`${newStaff.full_name} added to the team`, "success");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to add team member";
      setFormError(message);
      show(message, "error");
    } finally {
      setSubmitting(false);
    }
  }

  function openEdit(u: UserOut) {
    setEditUser(u);
    setEditForm({ full_name: u.full_name, position_id: u.position_id || positions[0]?.id || "" });
    setEditError(null);
  }

  async function handleEditSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token || !editUser) return;
    setEditError(null);
    setEditSubmitting(true);
    try {
      const updated = await api.updateBankStaff(token, editUser.id, editForm);
      setTeam((list) => list.map((x) => (x.id === updated.id ? updated : x)));
      setEditUser(null);
      show(`${updated.full_name} updated`, "success");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to update staff member";
      setEditError(message);
      show(message, "error");
    } finally {
      setEditSubmitting(false);
    }
  }

  async function handleToggleActive(u: UserOut) {
    if (!token) return;
    setTogglingId(u.id);
    try {
      const updated = u.is_active
        ? await api.deactivateBankStaff(token, u.id)
        : await api.reactivateBankStaff(token, u.id);
      setTeam((list) => list.map((x) => (x.id === updated.id ? updated : x)));
      show(`${updated.full_name} ${updated.is_active ? "reactivated" : "deactivated"}`, "success");
    } catch (err) {
      show(err instanceof ApiError ? err.message : "Failed to update staff member", "error");
    } finally {
      setTogglingId(null);
    }
  }

  if (!staffLoading && position && !position.can_manage_staff) {
    return (
      <Card className="mt-6 flex flex-col items-center gap-2 p-10 text-center">
        <IconLock className="h-8 w-8 text-slate-300" />
        <h1 className="text-sm font-semibold text-slate-900">Restricted</h1>
        <p className="text-sm text-slate-400">Your position ({position.title}) doesn&apos;t include staff management.</p>
      </Card>
    );
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Team</h1>
          <p className="mt-1 text-sm text-slate-500">Staff registered under your bank.</p>
        </div>
        <Button onClick={() => setModalOpen(true)} disabled={positions.length === 0}>
          <IconUserPlus className="h-4 w-4" />
          Add staff
        </Button>
      </div>

      {error && <div className="mt-4 rounded-lg bg-red-50 px-3.5 py-2.5 text-sm text-red-700">{error}</div>}

      <Card className="mt-6 overflow-hidden">
        <CardHeader title="Bank staff" subtitle={`${team.length} total`} />
        {loading ? (
          <TableSkeleton rows={3} cols={5} />
        ) : team.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-4 py-14 text-center">
            <IconUsers className="h-8 w-8 text-slate-300" />
            <p className="text-sm text-slate-400">No staff yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-left text-sm">
              <thead className="border-b border-slate-100 bg-slate-50/60 text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Email</th>
                  <th className="px-5 py-3 font-medium">Position</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {team.map((u) => {
                  const pos = positions.find((p) => p.id === u.position_id);
                  return (
                    <tr key={u.id} className={`transition-colors hover:bg-slate-50/60 ${u.is_active ? "" : "opacity-60"}`}>
                      <td className="px-5 py-3.5">
                        <div className="flex items-center gap-3">
                          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-100 text-xs font-semibold text-slate-600">
                            {initials(u.full_name)}
                          </div>
                          <span className="font-medium text-slate-900">{u.full_name}</span>
                        </div>
                      </td>
                      <td className="px-5 py-3.5 text-slate-500">{u.email}</td>
                      <td className="px-5 py-3.5">
                        {pos ? pos.title : <span className="text-slate-400">Unassigned</span>}
                      </td>
                      <td className="px-5 py-3.5">
                        <Badge tone={u.is_active ? "emerald" : "slate"}>{u.is_active ? "Active" : "Inactive"}</Badge>
                      </td>
                      <td className="px-5 py-3.5">
                        <div className="flex justify-end gap-2">
                          <button
                            type="button"
                            onClick={() => openEdit(u)}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
                          >
                            <IconPencil className="h-3.5 w-3.5" />
                            Edit
                          </button>
                          {u.id !== currentUser?.id && (
                            <Button
                              variant={u.is_active ? "secondary" : "primary"}
                              loading={togglingId === u.id}
                              onClick={() => handleToggleActive(u)}
                              className="px-3 py-1.5 text-xs"
                            >
                              {u.is_active ? "Deactivate" : "Reactivate"}
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Add staff member">
        <form onSubmit={handleCreate} className="space-y-4">
          <Field label="Full name">
            <Input
              required
              value={form.full_name}
              onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
              placeholder="Alex Officer"
            />
          </Field>
          <Field label="Email">
            <Input
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              placeholder="alex@bank.com"
            />
          </Field>
          <Field label="Temporary password" hint="At least 8 characters — share it securely with the new hire.">
            <Input
              type="password"
              required
              minLength={8}
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              placeholder="••••••••"
            />
          </Field>
          <Field label="Position">
            <Select
              required
              value={form.position_id}
              onChange={(e) => setForm((f) => ({ ...f, position_id: e.target.value }))}
            >
              {positions.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                  {p.max_approval_amount ? ` — up to $${Number(p.max_approval_amount).toLocaleString()}` : " — unlimited"}
                </option>
              ))}
            </Select>
          </Field>

          {formError && <p className="text-sm text-red-600">{formError}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={submitting}>
              Add staff
            </Button>
          </div>
        </form>
      </Modal>

      <Modal open={editUser !== null} onClose={() => setEditUser(null)} title="Edit staff member">
        <form onSubmit={handleEditSubmit} className="space-y-4">
          <Field label="Full name">
            <Input
              required
              value={editForm.full_name}
              onChange={(e) => setEditForm((f) => ({ ...f, full_name: e.target.value }))}
            />
          </Field>
          <Field label="Position">
            <Select
              required
              value={editForm.position_id}
              onChange={(e) => setEditForm((f) => ({ ...f, position_id: e.target.value }))}
            >
              {positions.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.title}
                  {p.max_approval_amount ? ` — up to $${Number(p.max_approval_amount).toLocaleString()}` : " — unlimited"}
                </option>
              ))}
            </Select>
          </Field>

          {editError && <p className="text-sm text-red-600">{editError}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setEditUser(null)}>
              Cancel
            </Button>
            <Button type="submit" loading={editSubmitting}>
              Save changes
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
