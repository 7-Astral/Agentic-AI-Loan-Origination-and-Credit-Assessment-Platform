"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";
import { api, type UserOut, type BankOut, type BankPositionOut, ApiError } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { Card, CardHeader } from "@/components/ui/Card";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Field, Input, Select } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { IconUserPlus, IconUsers } from "@/components/icons";

function initials(name: string) {
  return name.split(" ").map((p) => p[0]).slice(0, 2).join("").toUpperCase();
}

export default function AdminUsers() {
  const { token, user: currentUser } = useAuth();
  const { show } = useToast();
  const [users, setUsers] = useState<UserOut[]>([]);
  const [banks, setBanks] = useState<BankOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState({ full_name: "", email: "", password: "", bank_id: "", position_id: "" });
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [positions, setPositions] = useState<BankPositionOut[]>([]);
  const [positionsLoading, setPositionsLoading] = useState(false);

  const [tab, setTab] = useState<"customer" | "staff" | "admin">("staff");

  function loadUsers(t: string) {
    setLoading(true);
    Promise.all([api.users(t), api.banks(t)])
      .then(([u, b]) => {
        setUsers(u);
        setBanks(b);
        setForm((f) => ({ ...f, bank_id: f.bank_id || b[0]?.id || "" }));
      })
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (!token) return;
    loadUsers(token);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  useEffect(() => {
    if (!token || !form.bank_id) {
      setPositions([]);
      return;
    }
    setPositionsLoading(true);
    api
      .bankPositionsForAdmin(token, form.bank_id)
      .then((p) => {
        setPositions(p);
        setForm((f) => (p.some((pos) => pos.id === f.position_id) ? f : { ...f, position_id: "" }));
      })
      .catch(() => setPositions([]))
      .finally(() => setPositionsLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, form.bank_id]);

  async function handleCreateStaff(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setFormError(null);
    setSubmitting(true);
    try {
      const newUser = await api.createStaff(token, { ...form, position_id: form.position_id || null });
      setUsers((u) => [...u, newUser]);
      setModalOpen(false);
      setForm({ full_name: "", email: "", password: "", bank_id: banks[0]?.id || "", position_id: "" });
      show(`${newUser.full_name} added as staff`, "success");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to create staff member";
      setFormError(message);
      show(message, "error");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleActive(u: UserOut) {
    if (!token) return;
    setTogglingId(u.id);
    try {
      const updated = u.is_active ? await api.deactivateUser(token, u.id) : await api.reactivateUser(token, u.id);
      setUsers((list) => list.map((x) => (x.id === updated.id ? updated : x)));
      show(`${updated.full_name} ${updated.is_active ? "reactivated" : "deactivated"}`, "success");
    } catch (err) {
      show(err instanceof ApiError ? err.message : "Failed to update account", "error");
    } finally {
      setTogglingId(null);
    }
  }

  const TABS: Array<{ key: "customer" | "staff" | "admin"; label: string }> = [
    { key: "customer", label: "Customers" },
    { key: "staff", label: "Staff" },
    { key: "admin", label: "Admins" },
  ];
  const counts = {
    customer: users.filter((u) => u.role === "customer").length,
    staff: users.filter((u) => u.role === "staff").length,
    admin: users.filter((u) => u.role === "admin").length,
  };
  const filtered = users.filter((u) => u.role === tab);

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Users</h1>
          <p className="mt-1 text-sm text-slate-500">All accounts across customer, staff and admin roles.</p>
        </div>
        {tab === "staff" && (
          <Button onClick={() => setModalOpen(true)} disabled={banks.length === 0}>
            <IconUserPlus className="h-4 w-4" />
            Add staff
          </Button>
        )}
      </div>

      {error && <div className="mt-4 rounded-lg bg-red-50 px-3.5 py-2.5 text-sm text-red-700">{error}</div>}

      <div className="mt-6 flex gap-1.5 border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`-mb-px flex items-center gap-1.5 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors ${
              tab === t.key
                ? "border-indigo-600 text-indigo-700"
                : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {t.label}
            <span
              className={`rounded-full px-1.5 py-0.5 text-xs ${
                tab === t.key ? "bg-indigo-50 text-indigo-700" : "bg-slate-100 text-slate-500"
              }`}
            >
              {counts[t.key]}
            </span>
          </button>
        ))}
      </div>

      <Card className="mt-4 overflow-hidden">
        <CardHeader title={TABS.find((t) => t.key === tab)?.label ?? ""} subtitle={`${filtered.length} total`} />
        {loading ? (
          <TableSkeleton rows={4} cols={5} />
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-4 py-14 text-center">
            <IconUsers className="h-8 w-8 text-slate-300" />
            <p className="text-sm text-slate-400">No {TABS.find((t) => t.key === tab)?.label.toLowerCase()} yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-left text-sm">
              <thead className="border-b border-slate-100 bg-slate-50/60 text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Email</th>
                  {tab === "staff" && <th className="px-5 py-3 font-medium">Bank</th>}
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filtered.map((u) => (
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
                    {tab === "staff" && (
                      <td className="px-5 py-3.5 text-slate-600">
                        {banks.find((b) => b.id === u.bank_id)?.name ?? <span className="text-slate-300">—</span>}
                      </td>
                    )}
                    <td className="px-5 py-3.5">
                      <Badge tone={u.is_active ? "emerald" : "slate"}>{u.is_active ? "Active" : "Inactive"}</Badge>
                    </td>
                    <td className="px-5 py-3.5 text-right">
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
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Add staff member">
        <form onSubmit={handleCreateStaff} className="space-y-4">
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
          <Field label="Bank">
            <Select
              required
              value={form.bank_id}
              onChange={(e) => setForm((f) => ({ ...f, bank_id: e.target.value }))}
            >
              {banks.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field
            label="Position"
            hint={positionsLoading ? "Loading positions…" : "Sets approval limit and management permissions. Optional."}
          >
            <Select
              value={form.position_id}
              onChange={(e) => setForm((f) => ({ ...f, position_id: e.target.value }))}
              disabled={positionsLoading || positions.length === 0}
            >
              <option value="">No position</option>
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
    </div>
  );
}
