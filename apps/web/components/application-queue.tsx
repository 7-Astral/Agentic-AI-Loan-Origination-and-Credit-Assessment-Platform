"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { AlertTriangle, FileQuestion, Landmark, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { listApplications } from "@/lib/api";
import { statusBadgeVariant, statusLabel } from "@/lib/application-status";
import type { ApplicationStatus, ApplicationSummary } from "@/lib/types/application";

type PageState = "loading" | "error" | "ready";
type QueueFilter = "queue" | ApplicationStatus | "all";
type SortKey = "newest" | "oldest" | "amount-desc" | "amount-asc";

const STATUS_ORDER: ApplicationStatus[] = ["draft", "submitted", "in_review", "decided"];

const FILTER_OPTIONS: { value: QueueFilter; label: string }[] = [
  { value: "queue", label: "Active queue (submitted & in review)" },
  { value: "all", label: "All statuses" },
  { value: "draft", label: "Draft" },
  { value: "submitted", label: "Submitted" },
  { value: "in_review", label: "In review" },
  { value: "decided", label: "Decided" },
];

const SORT_OPTIONS: { value: SortKey; label: string }[] = [
  { value: "newest", label: "Newest first" },
  { value: "oldest", label: "Oldest first" },
  { value: "amount-desc", label: "Amount: high to low" },
  { value: "amount-asc", label: "Amount: low to high" },
];

function matchesFilter(status: ApplicationStatus, filter: QueueFilter): boolean {
  if (filter === "all") return true;
  if (filter === "queue") return status === "submitted" || status === "in_review";
  return status === filter;
}

/** Shared by the officer queue (own bank) and the admin queue (every bank) — both call the
 * same `GET /applications`, which scopes the result by the caller's role server-side, so
 * this component never needs to know which one it's rendering for. `basePath` is the only
 * thing that differs between the two call sites (`/officer` vs `/admin`). */
export function ApplicationQueue({ title, basePath }: { title: string; basePath: string }) {
  const [pageState, setPageState] = useState<PageState>("loading");
  const [applications, setApplications] = useState<ApplicationSummary[]>([]);
  const [filter, setFilter] = useState<QueueFilter>("queue");
  const [sort, setSort] = useState<SortKey>("newest");

  useEffect(() => {
    let cancelled = false;

    listApplications()
      .then((result) => {
        if (cancelled) return;
        setApplications(result);
        setPageState("ready");
      })
      .catch(() => {
        if (!cancelled) setPageState("error");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const counts = useMemo(() => {
    const tally: Record<ApplicationStatus, number> = {
      draft: 0,
      submitted: 0,
      in_review: 0,
      decided: 0,
    };
    for (const application of applications) tally[application.status] += 1;
    return tally;
  }, [applications]);

  const visible = useMemo(() => {
    const filtered = applications.filter((application) =>
      matchesFilter(application.status, filter),
    );
    const sorted = [...filtered];
    sorted.sort((a, b) => {
      switch (sort) {
        case "newest":
          return b.created_at.localeCompare(a.created_at);
        case "oldest":
          return a.created_at.localeCompare(b.created_at);
        case "amount-desc":
          return Number(b.loan_amount) - Number(a.loan_amount);
        case "amount-asc":
          return Number(a.loan_amount) - Number(b.loan_amount);
      }
    });
    return sorted;
  }, [applications, filter, sort]);

  return (
    <div className="mx-auto w-full max-w-5xl p-4 sm:p-6">
      <header className="mb-6 flex items-center gap-2">
        <Landmark className="h-5 w-5 text-primary" aria-hidden="true" />
        <h1 className="text-lg font-semibold">{title}</h1>
      </header>

      {pageState === "ready" && (
        <div className="mb-4 flex flex-wrap gap-2">
          {STATUS_ORDER.map((status) => (
            <Badge key={status} variant={statusBadgeVariant(status)} className="capitalize">
              {statusLabel(status)}: {counts[status]}
            </Badge>
          ))}
        </div>
      )}

      <div className="mb-4 flex flex-wrap gap-3">
        <select
          value={filter}
          onChange={(event) => setFilter(event.target.value as QueueFilter)}
          className="h-9 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          {FILTER_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        <select
          value={sort}
          onChange={(event) => setSort(event.target.value as SortKey)}
          className="h-9 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        >
          {SORT_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      {pageState === "loading" && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border p-10 text-center text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />
          <p className="text-sm">Loading the queue...</p>
        </div>
      )}

      {pageState === "error" && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border p-10 text-center">
          <AlertTriangle className="h-6 w-6 text-amber-600" aria-hidden="true" />
          <p className="text-sm font-medium">Couldn&apos;t load the queue. Please try again.</p>
        </div>
      )}

      {pageState === "ready" && visible.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border p-10 text-center text-muted-foreground">
          <FileQuestion className="h-6 w-6" aria-hidden="true" />
          <p className="text-sm">No applications match this filter.</p>
        </div>
      )}

      {pageState === "ready" && visible.length > 0 && (
        <ul className="flex flex-col gap-2">
          {visible.map((application) => (
            <li
              key={application.id}
              className="rounded-lg border border-border transition-colors hover:border-primary"
            >
              <Link
                href={`${basePath}/${application.id}`}
                className="flex flex-wrap items-center justify-between gap-3 p-4 hover:bg-secondary/50"
              >
                <div className="flex flex-col gap-1">
                  <span className="font-medium">
                    {application.customer_name} · {application.product_name}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    ${Number(application.loan_amount).toLocaleString()} ·{" "}
                    {new Date(application.created_at).toLocaleDateString()}
                  </span>
                </div>
                <Badge variant={statusBadgeVariant(application.status)} className="capitalize">
                  {statusLabel(application.status)}
                </Badge>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
