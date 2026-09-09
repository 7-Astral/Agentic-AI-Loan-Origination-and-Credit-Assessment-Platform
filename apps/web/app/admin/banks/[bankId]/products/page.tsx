"use client";

import { Pencil, Plus, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogFooter, Field } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { useAdminData } from "@/lib/mock/admin-store";
import type { AdminProduct } from "@/lib/types/admin";
import { cn } from "@/lib/utils";

function formatCurrency(value: number): string {
  return `$${value.toLocaleString()}`;
}

function formatTerm(months: number): string {
  return months % 12 === 0 ? `${months / 12}y` : `${months}m`;
}

const EMPTY_FORM = {
  productCode: "",
  name: "",
  loanTypeCode: "",
  categoryCode: "",
  secured: false,
  minAmount: "",
  maxAmount: "",
  minTermMonths: "",
  maxTermMonths: "",
  interestRate: "",
  comparisonRate: "",
  rateType: "fixed" as "fixed" | "variable",
  establishmentFee: "",
  maxLvr: "",
  features: "",
};

type ProductForm = typeof EMPTY_FORM;

function productToForm(product: AdminProduct): ProductForm {
  return {
    productCode: product.productCode,
    name: product.name,
    loanTypeCode: product.loanTypeCode,
    categoryCode: product.categoryCode,
    secured: product.secured,
    minAmount: String(product.minAmount),
    maxAmount: String(product.maxAmount),
    minTermMonths: String(product.minTermMonths),
    maxTermMonths: String(product.maxTermMonths),
    interestRate: String(product.interestRate),
    comparisonRate: String(product.comparisonRate),
    rateType: product.rateType,
    establishmentFee: String(product.establishmentFee),
    maxLvr: product.maxLvr !== null ? String(product.maxLvr) : "",
    features: product.features.join(", "),
  };
}

export default function ProductsPage() {
  const { products, loanTypes, addProduct, updateProduct, deleteProduct } = useAdminData();

  const [dialog, setDialog] = useState<{ mode: "add" } | { mode: "edit"; productCode: string } | null>(null);
  const [form, setForm] = useState<ProductForm>(EMPTY_FORM);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const categoryOptions = useMemo(
    () => loanTypes.find((lt) => lt.code === form.loanTypeCode)?.categories ?? [],
    [loanTypes, form.loanTypeCode],
  );

  const categoryName = (loanTypeCode: string, categoryCode: string) =>
    loanTypes.find((lt) => lt.code === loanTypeCode)?.categories.find((c) => c.code === categoryCode)?.name ??
    categoryCode;

  function openAdd() {
    setForm({ ...EMPTY_FORM, loanTypeCode: loanTypes[0]?.code ?? "", categoryCode: loanTypes[0]?.categories[0]?.code ?? "" });
    setDialog({ mode: "add" });
  }

  function openEdit(product: AdminProduct) {
    setForm(productToForm(product));
    setDialog({ mode: "edit", productCode: product.productCode });
  }

  function submit() {
    if (!form.name.trim() || !form.loanTypeCode || !form.categoryCode) return;
    const product: AdminProduct = {
      productCode: form.productCode.trim() || `PRD-${Date.now().toString(36).toUpperCase()}`,
      name: form.name.trim(),
      loanTypeCode: form.loanTypeCode,
      categoryCode: form.categoryCode,
      secured: form.secured,
      minAmount: Number(form.minAmount) || 0,
      maxAmount: Number(form.maxAmount) || 0,
      minTermMonths: Number(form.minTermMonths) || 0,
      maxTermMonths: Number(form.maxTermMonths) || 0,
      interestRate: Number(form.interestRate) || 0,
      comparisonRate: Number(form.comparisonRate) || 0,
      rateType: form.rateType,
      establishmentFee: Number(form.establishmentFee) || 0,
      maxLvr: form.maxLvr.trim() === "" ? null : Number(form.maxLvr),
      features: form.features
        .split(",")
        .map((f) => f.trim())
        .filter(Boolean),
    };

    if (dialog?.mode === "edit") {
      updateProduct(dialog.productCode, product);
    } else {
      addProduct(product);
    }
    setDialog(null);
  }

  return (
    <div className="p-6 sm:p-10">
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Products</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            The loan products offered by this bank, with rates and eligibility ranges.
          </p>
        </div>
        <Button onClick={openAdd} disabled={loanTypes.length === 0}>
          <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
          Add product
        </Button>
      </div>

      {products.length === 0 ? (
        <div className="rounded-xl border border-dashed border-input bg-background py-16 text-center text-sm text-muted-foreground">
          No products yet. Add your first product to get started.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-border shadow-sm">
          <table className="w-full min-w-[1020px] text-left text-sm">
            <thead>
              <tr className="border-b border-border bg-secondary/50 text-xs uppercase tracking-wide text-muted-foreground">
                <th className="px-4 py-3 font-medium">Product</th>
                <th className="px-4 py-3 font-medium">Type / Category</th>
                <th className="px-4 py-3 font-medium">Secured</th>
                <th className="px-4 py-3 font-medium">Amount</th>
                <th className="px-4 py-3 font-medium">Term</th>
                <th className="px-4 py-3 font-medium">Rate</th>
                <th className="px-4 py-3 font-medium">Comparison</th>
                <th className="px-4 py-3 font-medium">Max LVR</th>
                <th className="px-4 py-3 font-medium">Est. fee</th>
                <th className="px-4 py-3 font-medium" />
              </tr>
            </thead>
            <tbody>
              {products.map((product, index) => (
                <tr
                  key={product.productCode}
                  className={cn(
                    "border-b border-border last:border-0 hover:bg-secondary/30",
                    index % 2 === 1 && "bg-secondary/10",
                  )}
                >
                  <td className="px-4 py-3">
                    <p className="font-medium">{product.name}</p>
                    <p className="text-xs text-muted-foreground">{product.productCode}</p>
                  </td>
                  <td className="px-4 py-3">
                    <p>{categoryName(product.loanTypeCode, product.categoryCode)}</p>
                    <p className="text-xs capitalize text-muted-foreground">{product.loanTypeCode}</p>
                  </td>
                  <td className="px-4 py-3">
                    <Badge variant={product.secured ? "secondary" : "outline"}>
                      {product.secured ? "Secured" : "Unsecured"}
                    </Badge>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    {formatCurrency(product.minAmount)} &ndash; {formatCurrency(product.maxAmount)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    {formatTerm(product.minTermMonths)} &ndash; {formatTerm(product.maxTermMonths)}
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">
                    {product.interestRate.toFixed(2)}%
                    <span className="ml-1 text-xs text-muted-foreground">{product.rateType}</span>
                  </td>
                  <td className="whitespace-nowrap px-4 py-3">{product.comparisonRate.toFixed(2)}%</td>
                  <td className="px-4 py-3">{product.maxLvr !== null ? `${product.maxLvr}%` : "—"}</td>
                  <td className="whitespace-nowrap px-4 py-3">{formatCurrency(product.establishmentFee)}</td>
                  <td className="px-4 py-3">
                    <div className="flex justify-end gap-1">
                      <Button variant="ghost" size="sm" onClick={() => openEdit(product)}>
                        <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => setConfirmDelete(product.productCode)}>
                        <Trash2 className="h-3.5 w-3.5 text-destructive" aria-hidden="true" />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <Dialog
        open={dialog !== null}
        onClose={() => setDialog(null)}
        title={dialog?.mode === "edit" ? "Edit product" : "Add product"}
        className="max-w-2xl"
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-4">
            <Field label="Product name" htmlFor="product-name">
              <Input
                id="product-name"
                value={form.name}
                onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
                placeholder="e.g. Standard Personal Loan"
                autoFocus
              />
            </Field>
            <Field label="Product code" htmlFor="product-code" hint="Auto-generated if left blank.">
              <Input
                id="product-code"
                value={form.productCode}
                onChange={(event) => setForm((prev) => ({ ...prev, productCode: event.target.value }))}
                placeholder="e.g. PL-STD-001"
              />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Loan type" htmlFor="product-loan-type">
              <Select
                id="product-loan-type"
                value={form.loanTypeCode}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    loanTypeCode: event.target.value,
                    categoryCode: loanTypes.find((lt) => lt.code === event.target.value)?.categories[0]?.code ?? "",
                  }))
                }
              >
                {loanTypes.map((lt) => (
                  <option key={lt.code} value={lt.code}>
                    {lt.name}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Category" htmlFor="product-category">
              <Select
                id="product-category"
                value={form.categoryCode}
                onChange={(event) => setForm((prev) => ({ ...prev, categoryCode: event.target.value }))}
              >
                {categoryOptions.map((category) => (
                  <option key={category.code} value={category.code}>
                    {category.name}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Min amount ($)" htmlFor="product-min-amount">
              <Input
                id="product-min-amount"
                type="number"
                value={form.minAmount}
                onChange={(event) => setForm((prev) => ({ ...prev, minAmount: event.target.value }))}
              />
            </Field>
            <Field label="Max amount ($)" htmlFor="product-max-amount">
              <Input
                id="product-max-amount"
                type="number"
                value={form.maxAmount}
                onChange={(event) => setForm((prev) => ({ ...prev, maxAmount: event.target.value }))}
              />
            </Field>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Min term (months)" htmlFor="product-min-term">
              <Input
                id="product-min-term"
                type="number"
                value={form.minTermMonths}
                onChange={(event) => setForm((prev) => ({ ...prev, minTermMonths: event.target.value }))}
              />
            </Field>
            <Field label="Max term (months)" htmlFor="product-max-term">
              <Input
                id="product-max-term"
                type="number"
                value={form.maxTermMonths}
                onChange={(event) => setForm((prev) => ({ ...prev, maxTermMonths: event.target.value }))}
              />
            </Field>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <Field label="Interest rate (%)" htmlFor="product-rate">
              <Input
                id="product-rate"
                type="number"
                step="0.01"
                value={form.interestRate}
                onChange={(event) => setForm((prev) => ({ ...prev, interestRate: event.target.value }))}
              />
            </Field>
            <Field label="Comparison rate (%)" htmlFor="product-comparison">
              <Input
                id="product-comparison"
                type="number"
                step="0.01"
                value={form.comparisonRate}
                onChange={(event) => setForm((prev) => ({ ...prev, comparisonRate: event.target.value }))}
              />
            </Field>
            <Field label="Rate type" htmlFor="product-rate-type">
              <Select
                id="product-rate-type"
                value={form.rateType}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, rateType: event.target.value as "fixed" | "variable" }))
                }
              >
                <option value="fixed">Fixed</option>
                <option value="variable">Variable</option>
              </Select>
            </Field>
          </div>

          <div className="grid grid-cols-3 gap-4">
            <Field label="Establishment fee ($)" htmlFor="product-fee">
              <Input
                id="product-fee"
                type="number"
                value={form.establishmentFee}
                onChange={(event) => setForm((prev) => ({ ...prev, establishmentFee: event.target.value }))}
              />
            </Field>
            <Field label="Max LVR (%)" htmlFor="product-lvr" hint="Leave blank if not applicable.">
              <Input
                id="product-lvr"
                type="number"
                value={form.maxLvr}
                onChange={(event) => setForm((prev) => ({ ...prev, maxLvr: event.target.value }))}
              />
            </Field>
            <Field label="Secured" htmlFor="product-secured">
              <label className="flex h-10 items-center gap-2 text-sm">
                <input
                  id="product-secured"
                  type="checkbox"
                  checked={form.secured}
                  onChange={(event) => setForm((prev) => ({ ...prev, secured: event.target.checked }))}
                  className="h-4 w-4 rounded border-input"
                />
                Secured loan
              </label>
            </Field>
          </div>

          <Field label="Features" htmlFor="product-features" hint="Comma-separated.">
            <Input
              id="product-features"
              value={form.features}
              onChange={(event) => setForm((prev) => ({ ...prev, features: event.target.value }))}
              placeholder="Offset account, Redraw available"
            />
          </Field>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" disabled={form.name.trim().length === 0}>
              {dialog?.mode === "edit" ? "Save changes" : "Add product"}
            </Button>
          </DialogFooter>
        </form>
      </Dialog>

      <Dialog open={confirmDelete !== null} onClose={() => setConfirmDelete(null)} title="Delete product?">
        <p className="text-sm text-muted-foreground">
          This removes the product from this bank&apos;s configuration. This can&apos;t be undone.
        </p>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setConfirmDelete(null)}>
            Cancel
          </Button>
          <Button
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            onClick={() => {
              if (confirmDelete) deleteProduct(confirmDelete);
              setConfirmDelete(null);
            }}
          >
            Delete
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
}
