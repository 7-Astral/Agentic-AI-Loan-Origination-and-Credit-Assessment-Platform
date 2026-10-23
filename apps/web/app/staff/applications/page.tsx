"use client";

import Link from "next/link";
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { IBM_Plex_Sans } from "next/font/google";
import { Banknote, Bell, Check, CircleCheck, Clock, Info, Search, TrendingUp } from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { useStaff } from "@/lib/staff-context";
import { api, type LoanApplicationOut, ApiError } from "@/lib/api";
import { DecideModal } from "@/components/applications/DecideModal";
import { fmtDate, fmtMoney, humanize, statusLabel } from "@/components/reports/format";
import { cn } from "@/lib/utils";


const plex = IBM_Plex_Sans({ subsets: ["latin"], weight: ["400", "500", "600", "700"] });

type Filter = "all" | "decision" | "approved" | "rejected";
type Sort = "newest" | "oldest" | "amount" | "score";

const FILTERS: { id: Filter; label: string; match: (a: LoanApplicationOut) => boolean }[] = [
  { id: "all", label: "All", match: () => true },
  { id: "decision", label: "Awaiting decision", match: (a) => a.status === "under_review" },
  { id: "approved", label: "Approved", match: (a) => a.status === "approved" || a.status === "disbursed" },
  { id: "rejected", label: "Declined", match: (a) => a.status === "rejected" },
];

function applicantName(a: LoanApplicationOut) {
  return a.applicant_legal_name || a.applicant_name || "—";
}

function initials(name: string) {
  return (
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((w) => w[0]!.toUpperCase())
      .join("") || "?"
  );
}


function duplicateIds(applications: LoanApplicationOut[]) {
  const groups = new Map<string, string[]>();
  for (const a of applications) {
    const key = `${a.applicant_id}|${a.product_id}|${a.requested_amount}`;
    groups.set(key, [...(groups.get(key) ?? []), a.id]);
  }
  return new Set([...groups.values()].filter((ids) => ids.length > 1).flat());
}

function StatCard({
  icon,
  tint,
  label,
  value,
  suffix,
}: {
  icon: ReactNode;
  tint: string;
  label: string;
  value: ReactNode;
  suffix?: string;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-slate-200/70 bg-white p-4 shadow-sm shadow-slate-200/50 sm:flex-row sm:items-center sm:gap-4">
      <span className={cn("flex h-12 w-12 shrink-0 items-center justify-center rounded-xl", tint)}>{icon}</span>
      <div className="min-w-0">
        <p className="text-[13px] text-slate-500">{label}</p>
        <p className="truncate text-[20px] font-bold sm:text-[24px] leading-tight tabular-nums text-slate-900">
          {value}
          {suffix && <span className="ml-1 text-[13px] font-normal text-slate-400">{suffix}</span>}
        </p>
      </div>
    </div>
  );
}

function ScoreBar({ score }: { score: number }) {
  const colour = score >= 80 ? "bg-[#3d8b5f]" : score >= 60 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2.5">
      <div className="h-1.5 w-14 overflow-hidden rounded-full bg-slate-200" aria-hidden="true">
        <div className={cn("h-full rounded-full", colour)} style={{ width: `${Math.min(score, 100)}%` }} />
      </div>
      <span className="text-[14px] font-semibold tabular-nums text-slate-900">{score.toFixed(1)}</span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  if (status === "approved" || status === "disbursed")
    return (
      <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full bg-emerald-50 px-2.5 py-1 text-[12px] font-medium text-emerald-700">
        <Check className="h-3.5 w-3.5" aria-hidden="true" />
        {statusLabel(status)}
      </span>
    );
  const styles: Record<string, string> = { under_review: "bg-amber-50 text-amber-800", rejected: "bg-red-50 text-red-700" };
  const dots: Record<string, string> = { under_review: "bg-amber-500", rejected: "bg-red-500" };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-[12px] font-medium",
        styles[status] ?? "bg-slate-100 text-slate-600",
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", dots[status] ?? "bg-slate-400")} aria-hidden="true" />
      {status === "rejected" ? "Declined" : statusLabel(status)}
    </span>
  );
}

export default function StaffApplications() {
  const { token } = useAuth();
  const { unreadCount } = useStaff();
  const [applications, setApplications] = useState<LoanApplicationOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [decideApp, setDecideApp] = useState<LoanApplicationOut | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [sort, setSort] = useState<Sort>("newest");
  const [query, setQuery] = useState("");

  function loadApplications() {
    if (!token) return;
    api
      .bankApplications(token)
      .then(setApplications)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load applications"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadApplications();
  }, [token]);

  const counts = useMemo(
    () => Object.fromEntries(FILTERS.map((f) => [f.id, applications.filter(f.match).length])) as Record<Filter, number>,
    [applications],
  );
  const duplicates = useMemo(() => duplicateIds(applications), [applications]);

  const stats = useMemo(() => {
    const awaiting = applications.filter((a) => a.status === "under_review");
    const month = new Date().toISOString().slice(0, 7);
    const approvedThisMonth = applications.filter(
      (a) => (a.status === "approved" || a.status === "disbursed") && a.created_at.slice(0, 7) === month,
    );
    const scored = applications.filter((a) => a.assessment_score != null);
    return {
      awaiting: awaiting.length,
      exposure: awaiting.reduce((sum, a) => sum + a.requested_amount, 0),
      approvedAmount: approvedThisMonth.reduce((sum, a) => sum + a.requested_amount, 0),
      avgScore: scored.length ? scored.reduce((sum, a) => sum + (a.assessment_score ?? 0), 0) / scored.length : null,
    };
  }, [applications]);

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    const match = FILTERS.find((f) => f.id === filter)!.match;
    const list = applications.filter(
      (a) =>
        match(a) &&
        (!q ||
          [applicantName(a), a.applicant_name, a.applicant_email, a.product_name, a.loan_type]
            .filter(Boolean)
            .some((v) => v!.toLowerCase().includes(q))),
    );
    const by: Record<Sort, (a: LoanApplicationOut, b: LoanApplicationOut) => number> = {
      newest: (a, b) => b.created_at.localeCompare(a.created_at),
      oldest: (a, b) => a.created_at.localeCompare(b.created_at),
      amount: (a, b) => b.requested_amount - a.requested_amount,
      score: (a, b) => (b.assessment_score ?? -1) - (a.assessment_score ?? -1),
    };
    return [...list].sort(by[sort]);
  }, [applications, filter, sort, query]);

  return (
    <div className={`${plex.className} -m-4 min-h-screen bg-[#f5f6f8] p-4 text-slate-900 antialiased sm:-m-6 sm:p-6 lg:-m-10 lg:p-10`}>
      <div className="mx-auto max-w-6xl space-y-6">
        {/* Header */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 className="text-[26px] font-bold tracking-tight">Loan applications</h1>
            <p className="mt-1 text-[14px] text-slate-500">Review AI assessments and record credit decisions.</p>
          </div>
          <div className="flex items-center gap-3">
            <label className="relative block flex-1 sm:w-[280px] sm:flex-none">
              <span className="sr-only">Search applications</span>
              <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" aria-hidden="true" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search name, email or product"
                className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 text-[14px] shadow-sm shadow-slate-200/50 placeholder:text-slate-400 focus:border-[#2f4fd8] focus:outline-none focus:ring-4 focus:ring-[#2f4fd8]/10"
              />
            </label>
            <Link
              href="/staff/notifications"
              aria-label={unreadCount ? `Notifications, ${unreadCount} unread` : "Notifications"}
              className="relative hidden h-10 w-10 shrink-0 items-center justify-center rounded-xl border lg:flex border-slate-200 bg-white text-slate-600 shadow-sm shadow-slate-200/50 hover:text-slate-900"
            >
              <Bell className="h-[18px] w-[18px]" aria-hidden="true" />
              {unreadCount > 0 && <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-red-500 ring-2 ring-white" />}
            </Link>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-3 sm:gap-4 xl:grid-cols-4">
          <StatCard icon={<Clock className="h-5 w-5 text-amber-700" />} tint="bg-amber-50" label="Awaiting decision" value={loading ? "—" : stats.awaiting} />
          <StatCard icon={<Banknote className="h-5 w-5 text-[#2f4fd8]" />} tint="bg-blue-50" label="Exposure pending" value={loading ? "—" : fmtMoney(stats.exposure)} />
          <StatCard
            icon={<CircleCheck className="h-5 w-5 text-emerald-700" />}
            tint="bg-emerald-50"
            label="Approved this month"
            value={loading ? "—" : fmtMoney(stats.approvedAmount)}
          />
          <StatCard
            icon={<TrendingUp className="h-5 w-5 text-violet-700" />}
            tint="bg-violet-50"
            label="Avg. AI score"
            value={loading || stats.avgScore === null ? "—" : stats.avgScore.toFixed(1)}
            suffix={stats.avgScore === null ? undefined : "/100"}
          />
        </div>

        {error && <div className="rounded-xl bg-red-50 px-4 py-3 text-[14px] text-red-700">{error}</div>}

        <div className="overflow-hidden rounded-2xl border border-slate-200/70 bg-white shadow-sm shadow-slate-200/50">
          <div className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
            <div role="tablist" aria-label="Filter applications" className="flex w-fit max-w-full gap-1 overflow-x-auto rounded-xl bg-slate-100 p-1">
              {FILTERS.map((f) => {
                const selected = f.id === filter;
                const highlight = f.id === "decision" && (counts.decision ?? 0) > 0;
                return (
                  <button
                    key={f.id}
                    type="button"
                    role="tab"
                    aria-selected={selected}
                    onClick={() => setFilter(f.id)}
                    className={cn(
                      "flex shrink-0 items-center gap-2 rounded-lg px-3 py-1.5 text-[13px] transition-colors",
                      selected ? "bg-white font-semibold text-slate-900 shadow-sm" : "text-slate-600 hover:text-slate-900",
                    )}
                  >
                    {f.label}
                    <span
                      className={cn(
                        "text-[11px] tabular-nums",
                        highlight
                          ? "flex h-5 min-w-[20px] items-center justify-center rounded-full bg-amber-400 px-1.5 font-semibold text-amber-950"
                          : "text-slate-400",
                      )}
                    >
                      {counts[f.id] ?? 0}
                    </span>
                  </button>
                );
              })}
            </div>
            <label className="flex items-center gap-2 text-[13px] text-slate-500">
              Sort by
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as Sort)}
                className="h-9 rounded-lg border border-slate-200 bg-white px-2.5 text-[13px] text-slate-900 focus:border-[#2f4fd8] focus:outline-none"
              >
                <option value="newest">Newest first</option>
                <option value="oldest">Oldest first</option>
                <option value="amount">Largest amount</option>
                <option value="score">Highest AI score</option>
              </select>
            </label>
          </div>

          {loading ? (
            <div className="space-y-2 px-5 pb-5">
              {[0, 1, 2].map((i) => (
                <div key={i} className="h-14 animate-pulse rounded-lg bg-slate-100" />
              ))}
            </div>
          ) : rows.length === 0 ? (
            <div className="border-t border-slate-100 px-5 py-14 text-center">
              <p className="text-[14px] text-slate-700">{applications.length === 0 ? "No applications yet." : "No applications match this view."}</p>
              {applications.length > 0 && (
                <button
                  type="button"
                  onClick={() => {
                    setFilter("all");
                    setQuery("");
                  }}
                  className="mt-2 text-[13px] font-medium text-[#2f4fd8] hover:underline"
                >
                  Clear filters
                </button>
              )}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[920px] text-left">
                <thead>
                  <tr className="border-y border-slate-100 bg-slate-50/70 text-[12px] text-slate-500">
                    <th className="px-5 py-3 font-medium">Applicant</th>
                    <th className="px-3 py-3 text-right font-medium">Amount</th>
                    <th className="px-3 py-3 font-medium">Product</th>
                    <th className="px-3 py-3 font-medium">AI score</th>
                    <th className="px-3 py-3 font-medium">Status</th>
                    <th className="px-3 py-3 font-medium">Submitted</th>
                    <th className="px-5 py-3">
                      <span className="sr-only">Actions</span>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {rows.map((a) => {
                    const name = applicantName(a);
                    const decided = a.status === "approved" || a.status === "disbursed" || a.status === "rejected";
                    const reportHref = `/staff/applications/${a.id}/report`;
                    const accountDiffers =
                      a.applicant_legal_name && a.applicant_name && a.applicant_legal_name.toLowerCase() !== a.applicant_name.toLowerCase();
                    return (
                      <tr key={a.id} className="transition-colors hover:bg-slate-50/70">
                        <td className="px-5 py-3.5">
                          <div className="flex items-center gap-3">
                            <span
                              className={cn(
                                "flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-[12px] font-semibold",
                                decided ? "bg-slate-100 text-slate-600" : "bg-blue-50 text-[#2f4fd8]",
                              )}
                            >
                              {initials(name)}
                            </span>
                            <div className="min-w-0">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="text-[14px] font-semibold text-slate-900">{name}</span>
                                {duplicates.has(a.id) && (
                                  <span
                                    className="rounded-full bg-orange-50 px-2 py-0.5 text-[11px] font-medium text-orange-700"
                                    title="Same customer, product and amount as another application"
                                  >
                                    Possible duplicate
                                  </span>
                                )}
                              </div>
                              <p className="truncate text-[12px] text-slate-500">
                                {a.applicant_email}
                                {accountDiffers && ` · account: ${a.applicant_name}`}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="whitespace-nowrap px-3 py-3.5 text-right">
                          <p className="text-[15px] font-bold tabular-nums text-slate-900">{fmtMoney(a.requested_amount)}</p>
                          {a.tenure_requested_months ? <p className="text-[12px] text-slate-500">{a.tenure_requested_months} months</p> : null}
                        </td>
                        <td className="px-3 py-3.5 text-[13px] text-slate-700">{a.product_name ?? humanize(a.loan_type)}</td>
                        <td className="px-3 py-3.5">
                          {a.assessment_score != null ? (
                            <ScoreBar score={a.assessment_score} />
                          ) : (
                            <span className="text-[12px] text-slate-400">{a.chat_session_id ? "Not assessed" : "Form — no AI score"}</span>
                          )}
                        </td>
                        <td className="px-3 py-3.5">
                          <StatusBadge status={a.status} />
                        </td>
                        <td className="whitespace-nowrap px-3 py-3.5">
                          <p className="text-[13px] text-slate-900">{fmtDate(a.created_at)}</p>
                          <p className="text-[12px] text-[#2f4fd8]">
                            {a.status === "under_review" ? a.pending_position_title ?? "Awaiting review" : decided ? "Decision logged" : ""}
                          </p>
                        </td>
                        <td className="whitespace-nowrap px-5 py-3.5 text-right">
                          <div className="inline-flex gap-2">
                            {a.chat_session_id && (
                              <Link
                                href={reportHref}
                                className="inline-flex h-9 items-center rounded-lg border border-slate-200 bg-white px-3.5 text-[13px] font-medium text-slate-800 transition-colors hover:bg-slate-50"
                              >
                                Report
                              </Link>
                            )}
                            {a.status === "under_review" && (
                              <button
                                type="button"
                                onClick={() => setDecideApp(a)}
                                className="inline-flex h-9 items-center rounded-lg bg-[#2f4fd8] px-4 text-[13px] font-semibold text-white shadow-sm transition-colors hover:bg-[#2641b8]"
                              >
                                Decide
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {!loading && rows.length > 0 && (
            <div className="flex flex-col gap-2 border-t border-slate-100 px-5 py-3 text-[12px] text-slate-500 sm:flex-row sm:items-center sm:justify-between">
              <span>
                Showing {rows.length} of {applications.length} application{applications.length === 1 ? "" : "s"}
              </span>
              <span className="flex items-center gap-1.5">
                <Info className="h-3.5 w-3.5" aria-hidden="true" />
                AI score is the Five C&apos;s recommendation only — decisions rest with your bank&apos;s approvers.
              </span>
            </div>
          )}
        </div>
      </div>

      <DecideModal application={decideApp} token={token} onClose={() => setDecideApp(null)} onDecided={loadApplications} />
    </div>
  );
}
