"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";
import { api, type BankOut, type BankPositionOut, ApiError } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { Card, CardHeader } from "@/components/ui/Card";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Field, Input, Select } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { IconBuilding, IconUsers } from "@/components/icons";

const EMPTY_BANK_FORM = { name: "", code: "", contact_email: "" };
const EMPTY_POSITION_FORM = {
  title: "",
  rank: "",
  max_approval_amount: "",
  can_manage_staff: false,
  can_manage_products: false,
};

export default function AdminBanks() {
  const { token } = useAuth();
  const { show } = useToast();
  const [banks, setBanks] = useState<BankOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_BANK_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [positionsBank, setPositionsBank] = useState<BankOut | null>(null);
  const [positions, setPositions] = useState<BankPositionOut[]>([]);
  const [positionsLoading, setPositionsLoading] = useState(false);
  const [positionForm, setPositionForm] = useState(EMPTY_POSITION_FORM);
  const [positionError, setPositionError] = useState<string | null>(null);
  const [positionSubmitting, setPositionSubmitting] = useState(false);

  function load(t: string) {
    api
      .banks(t)
      .then(setBanks)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    if (!token) return;
    load(token);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setFormError(null);
    setSubmitting(true);
    try {
      const newBank = await api.createBank(token, {
        name: form.name,
        code: form.code,
        contact_email: form.contact_email || undefined,
      });
      setBanks((b) => [...b, newBank]);
      setModalOpen(false);
      setForm(EMPTY_BANK_FORM);
      show(`${newBank.name} added — a starter "Branch Manager" position was created for it`, "success");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to add bank";
      setFormError(message);
      show(message, "error");
    } finally {
      setSubmitting(false);
    }
  }

  async function handleToggleActive(b: BankOut) {
    if (!token) return;
    setTogglingId(b.id);
    try {
      const updated = b.status === "active" ? await api.deactivateBank(token, b.id) : await api.reactivateBank(token, b.id);
      setBanks((list) => list.map((x) => (x.id === updated.id ? updated : x)));
      show(`${updated.name} ${updated.status === "active" ? "reactivated" : "deactivated"}`, "success");
    } catch (err) {
      show(err instanceof ApiError ? err.message : "Failed to update bank", "error");
    } finally {
      setTogglingId(null);
    }
  }

  function openPositions(b: BankOut) {
    if (!token) return;
    setPositionsBank(b);
    setPositionForm(EMPTY_POSITION_FORM);
    setPositionError(null);
    setPositionsLoading(true);
    api
      .bankPositionsForAdmin(token, b.id)
      .then(setPositions)
      .catch(() => setPositions([]))
      .finally(() => setPositionsLoading(false));
  }

  async function handleAddPosition(e: FormEvent) {
    e.preventDefault();
    if (!token || !positionsBank) return;
    setPositionError(null);
    setPositionSubmitting(true);
    try {
      const newPosition = await api.createBankPositionForAdmin(token, positionsBank.id, {
        title: positionForm.title,
        rank: Number(positionForm.rank),
        max_approval_amount: positionForm.max_approval_amount ? Number(positionForm.max_approval_amount) : null,
        can_manage_staff: positionForm.can_manage_staff,
        can_manage_products: positionForm.can_manage_products,
      });
      setPositions((p) => [...p, newPosition].sort((a, c) => a.rank - c.rank));
      setPositionForm(EMPTY_POSITION_FORM);
      show(`${newPosition.title} added to ${positionsBank.name}'s ladder`, "success");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to add position";
      setPositionError(message);
      show(message, "error");
    } finally {
      setPositionSubmitting(false);
    }
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Banks</h1>
          <p className="mt-1 text-sm text-slate-500">
            Onboard a new bank onto the platform, and manage its approval-ladder positions. There&apos;s no
            separate &quot;bank admin&quot; account — a bank is run by its own staff, so adding a bank creates a
            starter Branch Manager position; assign a staff member to it from Users.
          </p>
        </div>
        <Button onClick={() => setModalOpen(true)}>
          <IconBuilding className="h-4 w-4" />
          Add bank
        </Button>
      </div>

      {error && <div className="mt-4 rounded-lg bg-red-50 px-3.5 py-2.5 text-sm text-red-700">{error}</div>}

      <Card className="mt-6 overflow-hidden">
        <CardHeader title="Banks" subtitle={`${banks.length} total`} />
        {loading ? (
          <TableSkeleton rows={3} cols={4} />
        ) : banks.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-4 py-14 text-center">
            <IconBuilding className="h-8 w-8 text-slate-300" />
            <p className="text-sm text-slate-400">No banks yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px] text-left text-sm">
              <thead className="border-b border-slate-100 bg-slate-50/60 text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-5 py-3 font-medium">Name</th>
                  <th className="px-5 py-3 font-medium">Code</th>
                  <th className="px-5 py-3 font-medium">Contact email</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {banks.map((b) => (
                  <tr key={b.id} className={`transition-colors hover:bg-slate-50/60 ${b.status === "active" ? "" : "opacity-60"}`}>
                    <td className="px-5 py-3.5 font-medium text-slate-900">{b.name}</td>
                    <td className="px-5 py-3.5 text-slate-500">{b.code}</td>
                    <td className="px-5 py-3.5 text-slate-500">{b.contact_email ?? <span className="text-slate-300">—</span>}</td>
                    <td className="px-5 py-3.5">
                      <Badge tone={b.status === "active" ? "emerald" : "slate"}>
                        {b.status === "active" ? "Active" : "Inactive"}
                      </Badge>
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => openPositions(b)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
                        >
                          <IconUsers className="h-3.5 w-3.5" />
                          Positions
                        </button>
                        <Button
                          variant={b.status === "active" ? "secondary" : "primary"}
                          loading={togglingId === b.id}
                          onClick={() => handleToggleActive(b)}
                          className="px-2.5 py-1.5 text-xs"
                        >
                          {b.status === "active" ? "Deactivate" : "Reactivate"}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Add bank">
        <form onSubmit={handleCreate} className="space-y-4">
          <Field label="Bank name">
            <Input
              required
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="Second National Bank"
            />
          </Field>
          <Field label="Bank code" hint="A short, unique identifier — e.g. SNB001.">
            <Input
              required
              value={form.code}
              onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))}
              placeholder="SNB001"
            />
          </Field>
          <Field label="Contact email (optional)">
            <Input
              type="email"
              value={form.contact_email}
              onChange={(e) => setForm((f) => ({ ...f, contact_email: e.target.value }))}
              placeholder="contact@bank.com"
            />
          </Field>

          {formError && <p className="text-sm text-red-600">{formError}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={submitting}>
              Add bank
            </Button>
          </div>
        </form>
      </Modal>

      <Modal
        open={positionsBank !== null}
        onClose={() => setPositionsBank(null)}
        title={positionsBank ? `${positionsBank.name} — positions` : "Positions"}
        widthClassName="sm:max-w-lg"
      >
        {positionsLoading ? (
          <p className="text-sm text-slate-400">Loading…</p>
        ) : (
          <div className="space-y-4">
            {positions.length === 0 ? (
              <p className="text-sm text-slate-400">No positions yet.</p>
            ) : (
              <ul className="divide-y divide-slate-100 rounded-lg border border-slate-200">
                {positions.map((p) => (
                  <li key={p.id} className="flex items-center justify-between px-3.5 py-2.5 text-sm">
                    <div>
                      <p className="font-medium text-slate-900">{p.title}</p>
                      <p className="text-xs text-slate-400">
                        Rank {p.rank} ·{" "}
                        {p.max_approval_amount ? `up to $${Number(p.max_approval_amount).toLocaleString()}` : "unlimited"}
                      </p>
                    </div>
                    <div className="flex gap-1.5">
                      {p.can_manage_staff && <Badge tone="indigo">Staff</Badge>}
                      {p.can_manage_products && <Badge tone="indigo">Products</Badge>}
                    </div>
                  </li>
                ))}
              </ul>
            )}

            <form onSubmit={handleAddPosition} className="space-y-3 border-t border-slate-100 pt-4">
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Add a position</p>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Title">
                  <Input
                    required
                    value={positionForm.title}
                    onChange={(e) => setPositionForm((f) => ({ ...f, title: e.target.value }))}
                    placeholder="Credit Manager"
                  />
                </Field>
                <Field label="Rank" hint="Lower ranks are checked first.">
                  <Input
                    type="number"
                    required
                    min={1}
                    value={positionForm.rank}
                    onChange={(e) => setPositionForm((f) => ({ ...f, rank: e.target.value }))}
                    placeholder="2"
                  />
                </Field>
              </div>
              <Field label="Max approval amount ($)" hint="Leave blank for unlimited.">
                <Input
                  type="number"
                  min={0}
                  value={positionForm.max_approval_amount}
                  onChange={(e) => setPositionForm((f) => ({ ...f, max_approval_amount: e.target.value }))}
                  placeholder="50000"
                />
              </Field>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={positionForm.can_manage_staff}
                    onChange={(e) => setPositionForm((f) => ({ ...f, can_manage_staff: e.target.checked }))}
                    className="h-4 w-4 rounded border-slate-300"
                  />
                  Can manage staff
                </label>
                <label className="flex items-center gap-2 text-sm text-slate-700">
                  <input
                    type="checkbox"
                    checked={positionForm.can_manage_products}
                    onChange={(e) => setPositionForm((f) => ({ ...f, can_manage_products: e.target.checked }))}
                    className="h-4 w-4 rounded border-slate-300"
                  />
                  Can manage products
                </label>
              </div>

              {positionError && <p className="text-sm text-red-600">{positionError}</p>}

              <div className="flex justify-end pt-1">
                <Button type="submit" loading={positionSubmitting} className="px-3 py-1.5 text-xs">
                  Add position
                </Button>
              </div>
            </form>
          </div>
        )}
      </Modal>
    </div>
  );
}
