"use client";

import { Pencil, Plus } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogFooter, Field } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useAdminData } from "@/lib/mock/admin-store";

export default function LoanTypesPage() {
  const { loanTypes, addLoanType, updateLoanType, addCategory, renameCategory } = useAdminData();

  const [typeDialog, setTypeDialog] = useState<{ mode: "add" } | { mode: "edit"; code: string } | null>(
    null,
  );
  const [typeForm, setTypeForm] = useState({ code: "", name: "", description: "" });

  const [categoryDialog, setCategoryDialog] = useState<
    | { mode: "add"; loanTypeCode: string }
    | { mode: "edit"; loanTypeCode: string; categoryCode: string }
    | null
  >(null);
  const [categoryForm, setCategoryForm] = useState({ code: "", name: "" });

  function openAddType() {
    setTypeForm({ code: "", name: "", description: "" });
    setTypeDialog({ mode: "add" });
  }

  function openEditType(code: string) {
    const loanType = loanTypes.find((lt) => lt.code === code);
    if (!loanType) return;
    setTypeForm({ code: loanType.code, name: loanType.name, description: loanType.description });
    setTypeDialog({ mode: "edit", code });
  }

  function submitType() {
    if (!typeForm.name.trim()) return;
    if (typeDialog?.mode === "add") {
      const code = typeForm.code.trim() || typeForm.name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_");
      addLoanType({ code, name: typeForm.name.trim(), description: typeForm.description.trim() });
    } else if (typeDialog?.mode === "edit") {
      updateLoanType(typeDialog.code, { name: typeForm.name.trim(), description: typeForm.description.trim() });
    }
    setTypeDialog(null);
  }

  function openAddCategory(loanTypeCode: string) {
    setCategoryForm({ code: "", name: "" });
    setCategoryDialog({ mode: "add", loanTypeCode });
  }

  function openEditCategory(loanTypeCode: string, categoryCode: string, name: string) {
    setCategoryForm({ code: categoryCode, name });
    setCategoryDialog({ mode: "edit", loanTypeCode, categoryCode });
  }

  function submitCategory() {
    if (!categoryForm.name.trim() || !categoryDialog) return;
    if (categoryDialog.mode === "add") {
      const code = categoryForm.code.trim() || categoryForm.name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_");
      addCategory(categoryDialog.loanTypeCode, { code, name: categoryForm.name.trim() });
    } else {
      renameCategory(categoryDialog.loanTypeCode, categoryDialog.categoryCode, categoryForm.name.trim());
    }
    setCategoryDialog(null);
  }

  return (
    <div className="mx-auto max-w-4xl p-6 sm:p-10">
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Loan Types</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            The loan types and categories offered by this bank, shown to applicants during discovery.
          </p>
        </div>
        <Button onClick={openAddType}>
          <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
          Add loan type
        </Button>
      </div>

      <div className="space-y-4">
        {loanTypes.map((loanType) => (
          <div
            key={loanType.code}
            className="rounded-xl border border-border bg-background p-5 shadow-sm transition-shadow hover:shadow-md"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="font-semibold">{loanType.name}</h2>
                  <Badge variant="outline" className="font-mono text-[10px]">
                    {loanType.code}
                  </Badge>
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{loanType.description}</p>
              </div>
              <Button variant="ghost" size="sm" onClick={() => openEditType(loanType.code)}>
                <Pencil className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
                Edit
              </Button>
            </div>

            <div className="mt-4 border-t border-border pt-4">
              <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Categories
              </p>
              <div className="flex flex-wrap gap-2">
                {loanType.categories.map((category) => (
                  <span
                    key={category.code}
                    className="flex items-center gap-2 rounded-full border border-input py-1 pl-3 pr-1 text-sm"
                  >
                    {category.name}
                    <button
                      type="button"
                      onClick={() => openEditCategory(loanType.code, category.code, category.name)}
                      aria-label={`Edit ${category.name}`}
                      className="rounded-full p-1 text-muted-foreground hover:bg-secondary hover:text-foreground"
                    >
                      <Pencil className="h-3 w-3" aria-hidden="true" />
                    </button>
                  </span>
                ))}
                <button
                  type="button"
                  onClick={() => openAddCategory(loanType.code)}
                  className="flex items-center gap-1 rounded-full border border-dashed border-input px-3 py-1 text-sm text-muted-foreground hover:border-primary hover:text-primary"
                >
                  <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                  Add category
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      <Dialog
        open={typeDialog !== null}
        onClose={() => setTypeDialog(null)}
        title={typeDialog?.mode === "edit" ? "Edit loan type" : "Add loan type"}
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            submitType();
          }}
          className="space-y-4"
        >
          {typeDialog?.mode === "add" && (
            <Field label="Code" htmlFor="type-code" hint="Lowercase, no spaces. Auto-generated if left blank.">
              <Input
                id="type-code"
                value={typeForm.code}
                onChange={(event) => setTypeForm((prev) => ({ ...prev, code: event.target.value }))}
                placeholder="e.g. personal"
              />
            </Field>
          )}
          <Field label="Name" htmlFor="type-name">
            <Input
              id="type-name"
              value={typeForm.name}
              onChange={(event) => setTypeForm((prev) => ({ ...prev, name: event.target.value }))}
              placeholder="e.g. Personal Loan"
              autoFocus
            />
          </Field>
          <Field label="Description" htmlFor="type-description">
            <Textarea
              id="type-description"
              value={typeForm.description}
              onChange={(event) => setTypeForm((prev) => ({ ...prev, description: event.target.value }))}
              placeholder="Shown to admins, not applicants."
              rows={3}
            />
          </Field>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setTypeDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" disabled={typeForm.name.trim().length === 0}>
              {typeDialog?.mode === "edit" ? "Save changes" : "Add loan type"}
            </Button>
          </DialogFooter>
        </form>
      </Dialog>

      <Dialog
        open={categoryDialog !== null}
        onClose={() => setCategoryDialog(null)}
        title={categoryDialog?.mode === "edit" ? "Edit category" : "Add category"}
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            submitCategory();
          }}
          className="space-y-4"
        >
          {categoryDialog?.mode === "add" && (
            <Field label="Code" htmlFor="category-code" hint="Lowercase, no spaces. Auto-generated if left blank.">
              <Input
                id="category-code"
                value={categoryForm.code}
                onChange={(event) => setCategoryForm((prev) => ({ ...prev, code: event.target.value }))}
                placeholder="e.g. vehicle"
              />
            </Field>
          )}
          <Field label="Name" htmlFor="category-name">
            <Input
              id="category-name"
              value={categoryForm.name}
              onChange={(event) => setCategoryForm((prev) => ({ ...prev, name: event.target.value }))}
              placeholder="e.g. Vehicle"
              autoFocus
            />
          </Field>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setCategoryDialog(null)}>
              Cancel
            </Button>
            <Button type="submit" disabled={categoryForm.name.trim().length === 0}>
              {categoryDialog?.mode === "edit" ? "Save changes" : "Add category"}
            </Button>
          </DialogFooter>
        </form>
      </Dialog>
    </div>
  );
}
