"use client";

import { Pencil, Plus, Trash2, X } from "lucide-react";
import { useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogFooter, Field } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Tabs } from "@/components/ui/tabs";
import { useAdminData } from "@/lib/mock/admin-store";
import type { AdminRule, AdminRuleFramework, AdminRuleStatus } from "@/lib/types/admin";
import { cn } from "@/lib/utils";

const STATUS_META: Record<AdminRuleStatus, { dot: string; border: string; pill: string; label: string }> = {
  fail: {
    dot: "bg-destructive",
    border: "border-l-destructive",
    pill: "bg-destructive/10 text-destructive",
    label: "Fail",
  },
  flag: {
    dot: "bg-amber-500",
    border: "border-l-amber-500",
    pill: "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300",
    label: "Flag",
  },
  pass: {
    dot: "bg-emerald-500",
    border: "border-l-emerald-500",
    pill: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300",
    label: "Pass",
  },
};

const FRAMEWORK_TABS: { value: AdminRuleFramework; label: string }[] = [
  { value: "individual", label: "Individual" },
  { value: "business", label: "Business" },
];

const EMPTY_FORM = {
  ruleId: "",
  framework: "individual" as AdminRuleFramework,
  requires: [] as string[],
  when: "",
  status: "flag" as AdminRuleStatus,
  message: "",
};

type RuleForm = typeof EMPTY_FORM;

function ruleToForm(rule: AdminRule): RuleForm {
  return {
    ruleId: rule.ruleId,
    framework: rule.framework,
    requires: rule.requires,
    when: rule.when,
    status: rule.status,
    message: rule.message,
  };
}

function MetricTagEditor({ metrics, onChange }: { metrics: string[]; onChange: (next: string[]) => void }) {
  const [draft, setDraft] = useState("");

  function addMetric() {
    const trimmed = draft.trim();
    if (!trimmed || metrics.includes(trimmed)) {
      setDraft("");
      return;
    }
    onChange([...metrics, trimmed]);
    setDraft("");
  }

  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-1.5">
        {metrics.map((metric) => (
          <span
            key={metric}
            className="flex items-center gap-1 rounded-full border border-input bg-secondary/60 py-1 pl-2.5 pr-1 font-mono text-xs"
          >
            {metric}
            <button
              type="button"
              onClick={() => onChange(metrics.filter((m) => m !== metric))}
              aria-label={`Remove ${metric}`}
              className="rounded-full p-0.5 text-muted-foreground hover:bg-secondary hover:text-foreground"
            >
              <X className="h-3 w-3" aria-hidden="true" />
            </button>
          </span>
        ))}
        {metrics.length === 0 && <span className="text-xs text-muted-foreground">No metrics added yet.</span>}
      </div>
      <div className="flex gap-2">
        <Input
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              addMetric();
            }
          }}
          placeholder="e.g. nsr"
          className="h-8 text-sm"
        />
        <Button type="button" variant="outline" size="sm" onClick={addMetric}>
          <Plus className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
          Add metric
        </Button>
      </div>
    </div>
  );
}

export default function RulesPage() {
  const { rules, addRule, updateRule, deleteRule } = useAdminData();
  const [activeFramework, setActiveFramework] = useState<AdminRuleFramework>("individual");

  const [dialog, setDialog] = useState<{ mode: "add" } | { mode: "edit"; ruleId: string } | null>(null);
  const [form, setForm] = useState<RuleForm>(EMPTY_FORM);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const visibleRules = rules.filter((rule) => rule.framework === activeFramework);
  const statusCounts = (["fail", "flag", "pass"] as const).map((status) => ({
    status,
    count: visibleRules.filter((r) => r.status === status).length,
  }));

  function openAdd() {
    setForm({ ...EMPTY_FORM, framework: activeFramework });
    setDialog({ mode: "add" });
  }

  function openEdit(rule: AdminRule) {
    setForm(ruleToForm(rule));
    setDialog({ mode: "edit", ruleId: rule.ruleId });
  }

  function submit() {
    if (!form.ruleId.trim() || !form.when.trim() || !form.message.trim()) return;
    const rule: AdminRule = {
      ruleId: form.ruleId.trim(),
      framework: form.framework,
      requires: form.requires,
      when: form.when.trim(),
      status: form.status,
      message: form.message.trim(),
    };

    if (dialog?.mode === "edit") {
      updateRule(dialog.ruleId, rule);
    } else {
      addRule(rule);
    }
    setDialog(null);
  }

  return (
    <div className="mx-auto max-w-5xl p-6 sm:p-10">
      <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Assessment Rules</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Rule engine definitions that turn computed metrics into routing signals. Missing required
            inputs always resolve to &quot;provisional&quot;, never a false pass.
          </p>
        </div>
        <Button onClick={openAdd}>
          <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
          Add rule
        </Button>
      </div>

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <Tabs
          value={activeFramework}
          onChange={(value) => setActiveFramework(value as AdminRuleFramework)}
          items={FRAMEWORK_TABS.map((tab) => ({
            value: tab.value,
            label: `${tab.label} (${rules.filter((r) => r.framework === tab.value).length})`,
          }))}
        />
        {visibleRules.length > 0 && (
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            {statusCounts.map(({ status, count }) => (
              <span key={status} className="flex items-center gap-1.5">
                <span className={cn("h-2 w-2 rounded-full", STATUS_META[status].dot)} aria-hidden="true" />
                {count} {STATUS_META[status].label.toLowerCase()}
              </span>
            ))}
          </div>
        )}
      </div>

      {visibleRules.length === 0 ? (
        <div className="rounded-xl border border-dashed border-input bg-background py-16 text-center text-sm text-muted-foreground">
          No {activeFramework} rules yet.{" "}
          <button type="button" onClick={openAdd} className="text-primary underline underline-offset-2">
            Add one
          </button>
          .
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          {visibleRules.map((rule) => {
            const meta = STATUS_META[rule.status];
            return (
              <div
                key={rule.ruleId}
                className={cn(
                  "flex flex-col rounded-xl border border-border border-l-4 bg-background p-4 shadow-sm transition-shadow hover:shadow-md",
                  meta.border,
                )}
              >
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-mono text-sm font-semibold">{rule.ruleId}</h3>
                    <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide", meta.pill)}>
                      {meta.label}
                    </span>
                  </div>
                  <div className="flex shrink-0 gap-0.5">
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => openEdit(rule)}>
                      <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
                    </Button>
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0" onClick={() => setConfirmDelete(rule.ruleId)}>
                      <Trash2 className="h-3.5 w-3.5 text-destructive" aria-hidden="true" />
                    </Button>
                  </div>
                </div>

                <div className="space-y-2 text-sm">
                  <div className="flex gap-2.5">
                    <span className="w-11 shrink-0 pt-1 text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                      If
                    </span>
                    <code className="min-w-0 flex-1 break-words rounded bg-secondary px-2 py-1 text-xs">
                      {rule.when}
                    </code>
                  </div>
                  <div className="flex gap-2.5">
                    <span className="w-11 shrink-0 pt-0.5 text-[10px] font-bold uppercase tracking-wide text-muted-foreground">
                      Then
                    </span>
                    <p className="min-w-0 flex-1">{rule.message}</p>
                  </div>
                </div>

                {rule.requires.length > 0 && (
                  <div className="mt-3 flex flex-wrap gap-1.5 border-t border-border pt-3">
                    {rule.requires.map((field) => (
                      <Badge key={field} variant="outline" className="font-mono text-[10px]">
                        {field}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      <Dialog
        open={dialog !== null}
        onClose={() => setDialog(null)}
        title={dialog?.mode === "edit" ? "Edit rule" : "Add rule"}
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-4">
            <Field label="Rule ID" htmlFor="rule-id">
              <Input
                id="rule-id"
                value={form.ruleId}
                onChange={(event) => setForm((prev) => ({ ...prev, ruleId: event.target.value }))}
                placeholder="e.g. dti_high"
                disabled={dialog?.mode === "edit"}
                autoFocus
              />
            </Field>
            <Field label="Framework" htmlFor="rule-framework">
              <Select
                id="rule-framework"
                value={form.framework}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, framework: event.target.value as AdminRuleFramework }))
                }
              >
                {FRAMEWORK_TABS.map((tab) => (
                  <option key={tab.value} value={tab.value}>
                    {tab.label}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <Field label="Requires" hint="Metrics this rule reads.">
            <MetricTagEditor
              metrics={form.requires}
              onChange={(requires) => setForm((prev) => ({ ...prev, requires }))}
            />
          </Field>

          <div className="grid grid-cols-2 gap-4">
            <Field label="Condition" htmlFor="rule-when" hint="A simpleeval expression.">
              <Input
                id="rule-when"
                value={form.when}
                onChange={(event) => setForm((prev) => ({ ...prev, when: event.target.value }))}
                placeholder="nsr < 1.0"
              />
            </Field>
            <Field label="Status" htmlFor="rule-status">
              <Select
                id="rule-status"
                value={form.status}
                onChange={(event) => setForm((prev) => ({ ...prev, status: event.target.value as AdminRuleStatus }))}
              >
                <option value="fail">Fail</option>
                <option value="flag">Flag</option>
                <option value="pass">Pass</option>
              </Select>
            </Field>
          </div>

          <Field label="Message" htmlFor="rule-message">
            <Input
              id="rule-message"
              value={form.message}
              onChange={(event) => setForm((prev) => ({ ...prev, message: event.target.value }))}
              placeholder="Shown alongside this rule's outcome"
            />
          </Field>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setDialog(null)}>
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={form.ruleId.trim().length === 0 || form.when.trim().length === 0 || form.message.trim().length === 0}
            >
              {dialog?.mode === "edit" ? "Save changes" : "Add rule"}
            </Button>
          </DialogFooter>
        </form>
      </Dialog>

      <Dialog open={confirmDelete !== null} onClose={() => setConfirmDelete(null)} title="Delete rule?">
        <p className="text-sm text-muted-foreground">
          This removes the rule from this bank&apos;s assessment engine. This can&apos;t be undone.
        </p>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setConfirmDelete(null)}>
            Cancel
          </Button>
          <Button
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            onClick={() => {
              if (confirmDelete) deleteRule(confirmDelete);
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
