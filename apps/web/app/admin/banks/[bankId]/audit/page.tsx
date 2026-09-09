"use client";

import { Bot, FileText, GitBranch, Lock, UserCog } from "lucide-react";
import { useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Tabs } from "@/components/ui/tabs";
import { useAdminData } from "@/lib/mock/admin-store";
import type { AdminAuditEvent, AdminAuditEventType } from "@/lib/types/admin";
import { cn } from "@/lib/utils";

const TYPE_META: Record<
  AdminAuditEventType,
  { label: string; icon: typeof Bot; iconBg: string; pill: string }
> = {
  llm_call: {
    label: "LLM Call",
    icon: Bot,
    iconBg: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
    pill: "bg-violet-100 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
  },
  decision: {
    label: "Decision",
    icon: GitBranch,
    iconBg: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
    pill: "bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  },
  document: {
    label: "Document",
    icon: FileText,
    iconBg: "bg-cyan-100 text-cyan-700 dark:bg-cyan-950 dark:text-cyan-300",
    pill: "bg-cyan-100 text-cyan-700 dark:bg-cyan-950 dark:text-cyan-300",
  },
  admin_change: {
    label: "Admin Change",
    icon: UserCog,
    iconBg: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    pill: "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  },
};

const FILTER_TABS: { value: "all" | AdminAuditEventType; label: string }[] = [
  { value: "all", label: "All" },
  { value: "llm_call", label: "LLM Calls" },
  { value: "decision", label: "Decisions" },
  { value: "document", label: "Documents" },
  { value: "admin_change", label: "Admin Changes" },
];

function formatTimestamp(iso: string): string {
  const [date, time] = iso.split("T");
  return `${date} ${time.slice(0, 5)} UTC`;
}

function detailLine(event: AdminAuditEvent): string {
  switch (event.type) {
    case "llm_call":
      return `${event.agent} · ${event.model} · ${event.latencyMs}ms · ${event.status}`;
    case "decision":
      return `${event.stage} → ${event.outcome}`;
    case "document":
      return `${event.documentType} · ${event.action}${event.outcome ? ` · ${event.outcome}` : ""}`;
    case "admin_change":
      return `${event.entity} ${event.action} by ${event.actor}`;
    default:
      return "";
  }
}

export default function AuditPage() {
  const { auditLog } = useAdminData();
  const [filter, setFilter] = useState<"all" | AdminAuditEventType>("all");

  const sorted = useMemo(
    () => [...auditLog].sort((a, b) => (a.timestamp < b.timestamp ? 1 : -1)),
    [auditLog],
  );
  const visible = filter === "all" ? sorted : sorted.filter((event) => event.type === filter);

  return (
    <div className="mx-auto max-w-4xl p-6 sm:p-10">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold tracking-tight">Audit Log</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Every LLM call, deterministic assessment decision, document event and admin change for this
          bank separated by type because only one of these categories ever involves a model.
        </p>
      </div>

      <div className="mb-6 flex gap-3 rounded-lg border border-input bg-secondary/30 p-3 text-xs text-muted-foreground">
        <Lock className="h-3.5 w-3.5 shrink-0 translate-y-0.5" aria-hidden="true" />
        <p>
          This log is read-only and append-only, audit entries can never be edited or deleted, by
          design.
        </p>
      </div>

      <Tabs
        className="mb-6"
        value={filter}
        onChange={(value) => setFilter(value as "all" | AdminAuditEventType)}
        items={FILTER_TABS.map((tab) => ({
          value: tab.value,
          label:
            tab.value === "all"
              ? `${tab.label} (${sorted.length})`
              : `${tab.label} (${sorted.filter((e) => e.type === tab.value).length})`,
        }))}
      />

      {visible.length === 0 ? (
        <div className="rounded-xl border border-dashed border-input bg-background py-16 text-center text-sm text-muted-foreground">
          No events of this type yet.
        </div>
      ) : (
        <div className="divide-y divide-border rounded-xl border border-border bg-background shadow-sm">
          {visible.map((event) => {
            const meta = TYPE_META[event.type];
            return (
              <div key={event.id} className="flex items-start gap-3 p-4">
                <span
                  className={cn(
                    "mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
                    meta.iconBg,
                  )}
                >
                  <meta.icon className="h-3.5 w-3.5" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={cn(
                        "rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
                        meta.pill,
                      )}
                    >
                      {meta.label}
                    </span>
                    {event.applicationId && (
                      <Badge variant="outline" className="font-mono text-[10px]">
                        {event.applicationId}
                      </Badge>
                    )}
                    <span className="font-mono text-[11px] text-muted-foreground">
                      {formatTimestamp(event.timestamp)}
                    </span>
                  </div>
                  <p className="mt-1 text-sm">{event.summary}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{detailLine(event)}</p>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
