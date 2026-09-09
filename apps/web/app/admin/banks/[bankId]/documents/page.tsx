"use client";

import { Check, Plus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Dialog, DialogFooter, Field } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useAdminData } from "@/lib/mock/admin-store";
import { cn } from "@/lib/utils";

export default function DocumentsPage() {
  const { loanTypes, documentTypes, documentRequirements, addDocumentType, toggleDocumentRequirement } =
    useAdminData();

  const [isAddOpen, setAddOpen] = useState(false);
  const [form, setForm] = useState({ code: "", name: "" });

  const columns = loanTypes.flatMap((loanType) =>
    loanType.categories.map((category) => ({
      loanTypeCode: loanType.code,
      loanTypeName: loanType.name,
      categoryCode: category.code,
      categoryName: category.name,
    })),
  );

  const isRequired = (documentTypeCode: string, loanTypeCode: string, categoryCode: string) =>
    documentRequirements.some(
      (req) =>
        req.documentTypeCode === documentTypeCode &&
        req.loanTypeCode === loanTypeCode &&
        req.categoryCode === categoryCode,
    );

  function submit() {
    if (!form.name.trim()) return;
    const code = form.code.trim() || form.name.trim().toLowerCase().replace(/[^a-z0-9]+/g, "_");
    addDocumentType({ code, name: form.name.trim() });
    setForm({ code: "", name: "" });
    setAddOpen(false);
  }

  return (
    <div className="p-6 sm:p-10">
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Document Requirements</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Which document types are required for each loan type and category. Click a cell to toggle it.
          </p>
        </div>
        <Button onClick={() => setAddOpen(true)}>
          <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
          Add document type
        </Button>
      </div>

      <div className="overflow-x-auto rounded-xl border border-border shadow-sm">
        <table className="text-sm">
          <thead>
            <tr className="border-b border-border bg-secondary/50 text-xs uppercase tracking-wide text-muted-foreground">
              <th className="sticky left-0 z-10 min-w-[220px] bg-secondary/50 px-4 py-3 text-left font-medium">
                Document type
              </th>
              {columns.map((column) => (
                <th
                  key={`${column.loanTypeCode}-${column.categoryCode}`}
                  className="min-w-[110px] px-3 py-3 text-center font-medium"
                >
                  <p className="capitalize text-foreground">{column.categoryName}</p>
                  <p className="font-normal normal-case text-muted-foreground">{column.loanTypeName}</p>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {documentTypes.map((docType, index) => (
              <tr
                key={docType.code}
                className={cn(
                  "border-b border-border last:border-0 hover:bg-secondary/20",
                  index % 2 === 1 && "bg-secondary/10",
                )}
              >
                <td className="sticky left-0 z-10 bg-background px-4 py-2.5 font-medium">{docType.name}</td>
                {columns.map((column) => {
                  const required = isRequired(docType.code, column.loanTypeCode, column.categoryCode);
                  return (
                    <td
                      key={`${column.loanTypeCode}-${column.categoryCode}`}
                      className="px-3 py-2.5 text-center"
                    >
                      <button
                        type="button"
                        onClick={() =>
                          toggleDocumentRequirement(docType.code, column.loanTypeCode, column.categoryCode)
                        }
                        aria-pressed={required}
                        aria-label={
                          required
                            ? `${docType.name} required for ${column.categoryName} — click to remove`
                            : `${docType.name} not required for ${column.categoryName} — click to add`
                        }
                        className={cn(
                          "mx-auto flex h-6 w-6 items-center justify-center rounded-md border transition-colors",
                          required
                            ? "border-primary bg-primary text-primary-foreground"
                            : "border-dashed border-input text-transparent hover:border-muted-foreground hover:bg-secondary",
                        )}
                      >
                        <Check className="h-3.5 w-3.5" aria-hidden="true" />
                      </button>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Dialog open={isAddOpen} onClose={() => setAddOpen(false)} title="Add document type">
        <form
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
          className="space-y-4"
        >
          <Field label="Name" htmlFor="doc-type-name">
            <Input
              id="doc-type-name"
              value={form.name}
              onChange={(event) => setForm((prev) => ({ ...prev, name: event.target.value }))}
              placeholder="e.g. Rates notice"
              autoFocus
            />
          </Field>
          <Field label="Code" htmlFor="doc-type-code" hint="Lowercase, no spaces. Auto-generated if left blank.">
            <Input
              id="doc-type-code"
              value={form.code}
              onChange={(event) => setForm((prev) => ({ ...prev, code: event.target.value }))}
              placeholder="e.g. rates_notice"
            />
          </Field>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setAddOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={form.name.trim().length === 0}>
              Add document type
            </Button>
          </DialogFooter>
        </form>
      </Dialog>
    </div>
  );
}
