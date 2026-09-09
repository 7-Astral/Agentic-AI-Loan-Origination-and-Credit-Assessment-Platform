"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Download, Upload } from "lucide-react";
import { Suspense, useRef, useState, type ChangeEvent } from "react";

import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { downloadCsv, parseCsv } from "@/lib/csv";
import { useAdminData } from "@/lib/mock/admin-store";
import type { AdminLoanPolicyRow, AdminLoanType } from "@/lib/types/admin";

type RowForm = AdminLoanPolicyRow;

const ROW_FIELD_LABELS: { key: keyof Omit<AdminLoanPolicyRow, "loanTypeCode" | "categoryCode">; label: string }[] = [
  { key: "minAge", label: "Min age" },
  { key: "residencyPolicy", label: "Residency policy" },
  { key: "depositLvrPolicy", label: "Deposit / LVR policy" },
  { key: "loanAmountRange", label: "Loan amount range" },
  { key: "maxTerm", label: "Max term" },
  { key: "incomeCashFlowPolicy", label: "Income / cash flow policy" },
  { key: "serviceabilityPolicy", label: "Serviceability policy" },
  { key: "creditPolicy", label: "Credit policy" },
];

const CSV_HEADER = ["Category", "Loan Type", ...ROW_FIELD_LABELS.map((f) => f.label)];

function blankRow(loanTypeCode: string, categoryCode: string): RowForm {
  return {
    loanTypeCode,
    categoryCode,
    minAge: "",
    residencyPolicy: "",
    depositLvrPolicy: "",
    loanAmountRange: "",
    maxTerm: "",
    incomeCashFlowPolicy: "",
    serviceabilityPolicy: "",
    creditPolicy: "",
  };
}

function normalizeHeader(header: string): string {
  return header.toLowerCase().replace(/[^a-z0-9]+/g, "");
}

function findCategory(label: string, loanTypes: AdminLoanType[]) {
  const target = label.trim().toLowerCase();
  if (!target) return null;
  for (const loanType of loanTypes) {
    for (const category of loanType.categories) {
      if (category.name.toLowerCase() === target) return { loanTypeCode: loanType.code, categoryCode: category.code };
    }
  }
  for (const loanType of loanTypes) {
    for (const category of loanType.categories) {
      const name = category.name.toLowerCase();
      if (target.includes(name) || name.includes(target)) {
        return { loanTypeCode: loanType.code, categoryCode: category.code };
      }
    }
  }
  return null;
}

function NewPolicyVersionForm({ bankId }: { bankId: string }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const cloneId = searchParams.get("clone");
  const { policyVersions, loanTypes, createPolicyVersion } = useAdminData();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const source =
    policyVersions.find((v) => v.id === cloneId) ?? policyVersions.find((v) => v.status === "active");

  const [versionLabel, setVersionLabel] = useState("");
  const [effectiveFrom, setEffectiveFrom] = useState(() => new Date().toISOString().slice(0, 10));
  const [notes, setNotes] = useState("");
  const [importStatus, setImportStatus] = useState<string | null>(null);

  const [rows, setRows] = useState<RowForm[]>(() =>
    loanTypes.flatMap((loanType) =>
      loanType.categories.map((category) => {
        const existing = source?.loanPolicyRows.find(
          (row) => row.loanTypeCode === loanType.code && row.categoryCode === category.code,
        );
        return existing ? { ...existing } : blankRow(loanType.code, category.code);
      }),
    ),
  );

  function updateRow(loanTypeCode: string, categoryCode: string, patch: Partial<RowForm>) {
    setRows((prev) =>
      prev.map((row) =>
        row.loanTypeCode === loanTypeCode && row.categoryCode === categoryCode ? { ...row, ...patch } : row,
      ),
    );
  }

  function categoryLabel(loanTypeCode: string, categoryCode: string) {
    const loanType = loanTypes.find((lt) => lt.code === loanTypeCode);
    return {
      loanTypeName: loanType?.name ?? loanTypeCode,
      categoryName: loanType?.categories.find((c) => c.code === categoryCode)?.name ?? categoryCode,
    };
  }

  function exportCsv() {
    const csvRows = [
      CSV_HEADER,
      ...rows.map((row) => {
        const { loanTypeName, categoryName } = categoryLabel(row.loanTypeCode, row.categoryCode);
        return [categoryName, loanTypeName, ...ROW_FIELD_LABELS.map((f) => row[f.key])];
      }),
    ];
    downloadCsv(`${bankId}-policy-loan-rows.csv`, csvRows);
  }

  function handleFileSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result ?? "");
      const table = parseCsv(text);
      if (table.length < 2) {
        setImportStatus(`${file.name}: no data rows found.`);
        return;
      }

      const [header, ...dataRows] = table;
      const normalized = header.map(normalizeHeader);
      const categoryColumn = normalized.findIndex((h) => h === "category" || h === "loantype");
      const fieldColumns = ROW_FIELD_LABELS.map((field) => ({
        key: field.key,
        index: normalized.findIndex((h) => h === normalizeHeader(field.label)),
      }));

      let matched = 0;
      let skipped = 0;

      for (const dataRow of dataRows) {
        const label = categoryColumn >= 0 ? dataRow[categoryColumn] : "";
        const match = findCategory(label ?? "", loanTypes);
        if (!match) {
          skipped++;
          continue;
        }
        const patch: Partial<RowForm> = {};
        for (const { key, index } of fieldColumns) {
          if (index >= 0 && dataRow[index] !== undefined) {
            patch[key] = dataRow[index];
          }
        }
        updateRow(match.loanTypeCode, match.categoryCode, patch);
        matched++;
      }

      setImportStatus(
        skipped > 0
          ? `${file.name}: matched ${matched} row${matched === 1 ? "" : "s"}, skipped ${skipped} unrecognized.`
          : `${file.name}: matched ${matched} row${matched === 1 ? "" : "s"}.`,
      );
    };
    reader.readAsText(file);
  }

  function submit() {
    if (!versionLabel.trim() || !effectiveFrom) return;
    createPolicyVersion({
      version: versionLabel.trim(),
      effectiveFrom,
      notes: notes.trim(),
      loanPolicyRows: rows,
    });
    router.push(`/admin/banks/${bankId}/policy`);
  }

  return (
    <div className="mx-auto max-w-4xl p-6 sm:p-10">
      <Link
        href={`/admin/banks/${bankId}/policy`}
        className="mb-6 flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Cancel
      </Link>

      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">New policy version</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          {source
            ? `Cloned from ${source.version} every field below starts as a copy, edit only what's changing.`
            : "Starting blank no existing version was found to clone from."}{" "}
          This creates a new, permanent version; it never modifies {source?.version ?? "an existing version"}.
        </p>
      </div>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          submit();
        }}
        className="space-y-10"
      >
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Field label="Version label" htmlFor="version-label" hint="e.g. 2026.10-v1">
            <Input
              id="version-label"
              value={versionLabel}
              onChange={(event) => setVersionLabel(event.target.value)}
              placeholder="2026.10-v1"
              autoFocus
            />
          </Field>
          <Field label="Effective from" htmlFor="effective-from">
            <Input
              id="effective-from"
              type="date"
              value={effectiveFrom}
              onChange={(event) => setEffectiveFrom(event.target.value)}
            />
          </Field>
          <Field label="Notes" htmlFor="version-notes" hint="Why this version exists.">
            <Textarea
              id="version-notes"
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              rows={1}
              className="min-h-[40px]"
            />
          </Field>
        </div>

        <div>
          <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Loan policy</h2>
            <div className="flex items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,text/csv"
                className="hidden"
                onChange={handleFileSelected}
              />
              <Button type="button" variant="outline" size="sm" onClick={exportCsv}>
                <Download className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
                Download CSV
              </Button>
              <Button type="button" variant="outline" size="sm" onClick={() => fileInputRef.current?.click()}>
                <Upload className="mr-2 h-3.5 w-3.5" aria-hidden="true" />
                Upload CSV
              </Button>
            </div>
          </div>
          {importStatus && <p className="mb-4 text-xs text-muted-foreground">{importStatus}</p>}

          <div className="space-y-4">
            {rows.map((row) => {
              const { loanTypeName, categoryName } = categoryLabel(row.loanTypeCode, row.categoryCode);
              return (
                <div
                  key={`${row.loanTypeCode}-${row.categoryCode}`}
                  className="rounded-lg border border-border bg-background p-4 shadow-sm"
                >
                  <h3 className="mb-3 text-sm font-semibold">
                    {categoryName} <span className="font-normal text-muted-foreground">— {loanTypeName}</span>
                  </h3>
                  <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                    {ROW_FIELD_LABELS.map(({ key, label }) => (
                      <Field key={key} label={label} htmlFor={`${row.loanTypeCode}-${row.categoryCode}-${key}`}>
                        <Input
                          id={`${row.loanTypeCode}-${row.categoryCode}-${key}`}
                          value={row[key]}
                          onChange={(event) =>
                            updateRow(row.loanTypeCode, row.categoryCode, { [key]: event.target.value })
                          }
                        />
                      </Field>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="flex justify-end gap-2 border-t border-border pt-6">
          <Link href={`/admin/banks/${bankId}/policy`}>
            <Button type="button" variant="ghost">
              Cancel
            </Button>
          </Link>
          <Button type="submit" disabled={versionLabel.trim().length === 0}>
            Create version
          </Button>
        </div>
      </form>
    </div>
  );
}

export default function NewPolicyVersionPage({ params }: { params: { bankId: string } }) {
  return (
    <Suspense fallback={null}>
      <NewPolicyVersionForm bankId={params.bankId} />
    </Suspense>
  );
}
