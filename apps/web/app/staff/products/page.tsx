"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useAuth } from "@/lib/auth-context";
import { useStaff } from "@/lib/staff-context";
import { api, type LoanProductOut, type UpdateLoanProductPayload, ApiError } from "@/lib/api";
import { useToast } from "@/components/ui/Toast";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Field, Input, Select } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { IconLock, IconPackage, IconPencil } from "@/components/icons";

const LOAN_TYPES = [
  { value: "personal", label: "Personal" },
  { value: "business", label: "Business" },
  { value: "home", label: "Home" },
  { value: "auto", label: "Auto" },
  { value: "education", label: "Education" },
];

const EMPTY_FORM = {
  product_type: "personal",
  name: "",
  min_amount: "",
  max_amount: "",
  interest_rate_min: "",
  interest_rate_max: "",
  tenure_min_months: "",
  tenure_max_months: "",
};

export default function StaffProducts() {
  const { token } = useAuth();
  const { position, loading: staffLoading } = useStaff();
  const { show } = useToast();
  const [products, setProducts] = useState<LoanProductOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [editProduct, setEditProduct] = useState<LoanProductOut | null>(null);
  const [editForm, setEditForm] = useState(EMPTY_FORM);
  const [editError, setEditError] = useState<string | null>(null);
  const [editSubmitting, setEditSubmitting] = useState(false);

  const [togglingId, setTogglingId] = useState<string | null>(null);

  function load(t: string) {
    api
      .bankProducts(t)
      .then(setProducts)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"));
  }

  useEffect(() => {
    if (!token) return;
    load(token);
  }, [token]);

  async function handleCreate(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setFormError(null);
    setSubmitting(true);
    try {
      const newProduct = await api.createBankProduct(token, {
        product_type: form.product_type,
        name: form.name,
        min_amount: Number(form.min_amount),
        max_amount: Number(form.max_amount),
        interest_rate_min: Number(form.interest_rate_min),
        interest_rate_max: Number(form.interest_rate_max),
        tenure_min_months: Number(form.tenure_min_months),
        tenure_max_months: Number(form.tenure_max_months),
      });
      setProducts((p) => [...(p ?? []), newProduct]);
      setModalOpen(false);
      setForm(EMPTY_FORM);
      show(`${newProduct.name} added`, "success");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to create product";
      setFormError(message);
      show(message, "error");
    } finally {
      setSubmitting(false);
    }
  }

  function openEdit(p: LoanProductOut) {
    setEditProduct(p);
    setEditForm({
      product_type: p.product_type,
      name: p.name,
      min_amount: String(p.min_amount),
      max_amount: String(p.max_amount),
      interest_rate_min: String(p.interest_rate_min),
      interest_rate_max: String(p.interest_rate_max),
      tenure_min_months: String(p.tenure_min_months),
      tenure_max_months: String(p.tenure_max_months),
    });
    setEditError(null);
  }

  async function handleEditSubmit(e: FormEvent) {
    e.preventDefault();
    if (!token || !editProduct) return;
    setEditError(null);
    setEditSubmitting(true);
    try {
      const payload: UpdateLoanProductPayload = {
        product_type: editForm.product_type,
        name: editForm.name,
        min_amount: Number(editForm.min_amount),
        max_amount: Number(editForm.max_amount),
        interest_rate_min: Number(editForm.interest_rate_min),
        interest_rate_max: Number(editForm.interest_rate_max),
        tenure_min_months: Number(editForm.tenure_min_months),
        tenure_max_months: Number(editForm.tenure_max_months),
      };
      const updated = await api.updateBankProduct(token, editProduct.id, payload);
      setProducts((list) => (list ?? []).map((x) => (x.id === updated.id ? updated : x)));
      setEditProduct(null);
      show(`${updated.name} updated`, "success");
    } catch (err) {
      const message = err instanceof ApiError ? err.message : "Failed to update product";
      setEditError(message);
      show(message, "error");
    } finally {
      setEditSubmitting(false);
    }
  }

  async function handleToggleActive(p: LoanProductOut) {
    if (!token) return;
    setTogglingId(p.id);
    try {
      const updated = p.is_active
        ? await api.deactivateBankProduct(token, p.id)
        : await api.reactivateBankProduct(token, p.id);
      setProducts((list) => (list ?? []).map((x) => (x.id === updated.id ? updated : x)));
      show(`${updated.name} ${updated.is_active ? "reactivated" : "deactivated"}`, "success");
    } catch (err) {
      show(err instanceof ApiError ? err.message : "Failed to update product", "error");
    } finally {
      setTogglingId(null);
    }
  }

  if (!staffLoading && position && !position.can_manage_products) {
    return (
      <Card className="mt-6 flex flex-col items-center gap-2 p-10 text-center">
        <IconLock className="h-8 w-8 text-slate-300" />
        <h1 className="text-sm font-semibold text-slate-900">Restricted</h1>
        <p className="text-sm text-slate-400">
          Your position ({position.title}) doesn&apos;t include product management.
        </p>
      </Card>
    );
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Loan products</h1>
          <p className="mt-1 text-sm text-slate-500">Products your bank offers to customers.</p>
        </div>
        <Button onClick={() => setModalOpen(true)}>
          <IconPackage className="h-4 w-4" />
          Add product
        </Button>
      </div>

      {error && <div className="mt-4 rounded-lg bg-red-50 px-3.5 py-2.5 text-sm text-red-700">{error}</div>}

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {products === null &&
          Array.from({ length: 3 }).map((_, i) => (
            <Card key={i} className="p-5">
              <Skeleton className="h-9 w-9 rounded-xl" />
              <Skeleton className="mt-4 h-4 w-2/3" />
              <Skeleton className="mt-3 h-3 w-full" />
              <Skeleton className="mt-2 h-3 w-3/4" />
            </Card>
          ))}

        {products?.map((p) => (
          <Card key={p.id} className={`p-5 ${p.is_active ? "" : "opacity-60"}`}>
            <div className="flex items-start justify-between gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                <IconPackage className="h-5 w-5" />
              </div>
              <div className="flex gap-1.5">
                <Badge tone="slate">{p.product_type}</Badge>
                <Badge tone={p.is_active ? "emerald" : "slate"}>{p.is_active ? "Active" : "Inactive"}</Badge>
              </div>
            </div>
            <h2 className="mt-3 font-semibold text-slate-900">{p.name}</h2>
            <dl className="mt-3 space-y-1.5 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-400">Amount</dt>
                <dd className="font-medium text-slate-700">
                  ${p.min_amount.toLocaleString()} – ${p.max_amount.toLocaleString()}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-400">Rate</dt>
                <dd className="font-medium text-slate-700">
                  {p.interest_rate_min}% – {p.interest_rate_max}%
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-400">Tenure</dt>
                <dd className="font-medium text-slate-700">
                  {p.tenure_min_months}–{p.tenure_max_months} mo
                </dd>
              </div>
            </dl>
            <div className="mt-4 flex gap-2">
              <button
                type="button"
                onClick={() => openEdit(p)}
                className="inline-flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1.5 text-xs font-medium text-slate-600 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
              >
                <IconPencil className="h-3.5 w-3.5" />
                Edit
              </button>
              <Button
                variant={p.is_active ? "secondary" : "primary"}
                loading={togglingId === p.id}
                onClick={() => handleToggleActive(p)}
                className="flex-1 px-2.5 py-1.5 text-xs"
              >
                {p.is_active ? "Deactivate" : "Reactivate"}
              </Button>
            </div>
          </Card>
        ))}

        {products?.length === 0 && <p className="text-sm text-slate-400">No products yet.</p>}
      </div>

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="Add loan product">
        <form onSubmit={handleCreate} className="space-y-4">
          <Field label="Product name">
            <Input
              required
              value={form.name}
              onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              placeholder="Everyday Personal Loan"
            />
          </Field>
          <Field label="Type">
            <Select
              value={form.product_type}
              onChange={(e) => setForm((f) => ({ ...f, product_type: e.target.value }))}
            >
              {LOAN_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </Select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Min amount ($)">
              <Input
                type="number"
                required
                min={0}
                value={form.min_amount}
                onChange={(e) => setForm((f) => ({ ...f, min_amount: e.target.value }))}
                placeholder="2000"
              />
            </Field>
            <Field label="Max amount ($)">
              <Input
                type="number"
                required
                min={0}
                value={form.max_amount}
                onChange={(e) => setForm((f) => ({ ...f, max_amount: e.target.value }))}
                placeholder="50000"
              />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Min rate (%)">
              <Input
                type="number"
                required
                step="0.1"
                min={0}
                value={form.interest_rate_min}
                onChange={(e) => setForm((f) => ({ ...f, interest_rate_min: e.target.value }))}
                placeholder="8.5"
              />
            </Field>
            <Field label="Max rate (%)">
              <Input
                type="number"
                required
                step="0.1"
                min={0}
                value={form.interest_rate_max}
                onChange={(e) => setForm((f) => ({ ...f, interest_rate_max: e.target.value }))}
                placeholder="15"
              />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Min tenure (mo)">
              <Input
                type="number"
                required
                min={1}
                value={form.tenure_min_months}
                onChange={(e) => setForm((f) => ({ ...f, tenure_min_months: e.target.value }))}
                placeholder="6"
              />
            </Field>
            <Field label="Max tenure (mo)">
              <Input
                type="number"
                required
                min={1}
                value={form.tenure_max_months}
                onChange={(e) => setForm((f) => ({ ...f, tenure_max_months: e.target.value }))}
                placeholder="60"
              />
            </Field>
          </div>

          {formError && <p className="text-sm text-red-600">{formError}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={submitting}>
              Add product
            </Button>
          </div>
        </form>
      </Modal>

      <Modal open={editProduct !== null} onClose={() => setEditProduct(null)} title="Edit loan product">
        <form onSubmit={handleEditSubmit} className="space-y-4">
          <Field label="Product name">
            <Input
              required
              value={editForm.name}
              onChange={(e) => setEditForm((f) => ({ ...f, name: e.target.value }))}
            />
          </Field>
          <Field label="Type">
            <Select
              value={editForm.product_type}
              onChange={(e) => setEditForm((f) => ({ ...f, product_type: e.target.value }))}
            >
              {LOAN_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </Select>
          </Field>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Min amount ($)">
              <Input
                type="number"
                required
                min={0}
                value={editForm.min_amount}
                onChange={(e) => setEditForm((f) => ({ ...f, min_amount: e.target.value }))}
              />
            </Field>
            <Field label="Max amount ($)">
              <Input
                type="number"
                required
                min={0}
                value={editForm.max_amount}
                onChange={(e) => setEditForm((f) => ({ ...f, max_amount: e.target.value }))}
              />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Min rate (%)">
              <Input
                type="number"
                required
                step="0.1"
                min={0}
                value={editForm.interest_rate_min}
                onChange={(e) => setEditForm((f) => ({ ...f, interest_rate_min: e.target.value }))}
              />
            </Field>
            <Field label="Max rate (%)">
              <Input
                type="number"
                required
                step="0.1"
                min={0}
                value={editForm.interest_rate_max}
                onChange={(e) => setEditForm((f) => ({ ...f, interest_rate_max: e.target.value }))}
              />
            </Field>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Min tenure (mo)">
              <Input
                type="number"
                required
                min={1}
                value={editForm.tenure_min_months}
                onChange={(e) => setEditForm((f) => ({ ...f, tenure_min_months: e.target.value }))}
              />
            </Field>
            <Field label="Max tenure (mo)">
              <Input
                type="number"
                required
                min={1}
                value={editForm.tenure_max_months}
                onChange={(e) => setEditForm((f) => ({ ...f, tenure_max_months: e.target.value }))}
              />
            </Field>
          </div>

          {editError && <p className="text-sm text-red-600">{editError}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="secondary" onClick={() => setEditProduct(null)}>
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
