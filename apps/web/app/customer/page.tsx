"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  CheckCircle2,
  Clock,
  FileText,
  Landmark,
  LogOut,
  MessageSquare,
  ShieldCheck,
  UserCheck,
  XCircle,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { api, type LoanApplicationOut } from "@/lib/api";
import { agentApi, type ResumeResponse } from "@/lib/agent-api";
import { cn } from "@/lib/utils";

const THEME = {
  "--primary": "165 76% 25%",
  "--primary-foreground": "0 0% 100%",
} as React.CSSProperties;

const STATUS: Record<string, { label: string; className: string; icon: typeof Clock }> = {
  draft: { label: "Draft", className: "bg-slate-100 text-slate-600", icon: FileText },
  submitted: { label: "Submitted", className: "bg-slate-100 text-slate-700", icon: Clock },
  under_review: { label: "Under review", className: "bg-amber-50 text-amber-700", icon: Clock },
  approved: { label: "Approved", className: "bg-emerald-50 text-emerald-700", icon: CheckCircle2 },
  rejected: { label: "Declined", className: "bg-red-50 text-red-700", icon: XCircle },
  disbursed: { label: "Funds sent", className: "bg-emerald-50 text-emerald-700", icon: CheckCircle2 },
};

function money(n: number) {
  return n.toLocaleString("en-AU", { style: "currency", currency: "AUD", maximumFractionDigits: 0 });
}

function lastAgentLine(res: ResumeResponse) {
  if (res.question) return res.question;
  const agent = [...res.messages].reverse().find((m) => m.role !== "user");
  return agent?.content ?? null;
}

export default function CustomerPortal() {
  const { user, token, loading, logout } = useAuth();
  const router = useRouter();

  const [applications, setApplications] = useState<LoanApplicationOut[]>([]);
  const [appsLoading, setAppsLoading] = useState(true);
  const [draft, setDraft] = useState<ResumeResponse | null>(null);

  useEffect(() => {
    if (!loading && (!user || user.role !== "customer")) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (!token) return;
    setAppsLoading(true);
    api
      .myApplications(token)
      .then(setApplications)
      .catch(() => {})
      .finally(() => setAppsLoading(false));
    agentApi
      .current(token)
      .then((res) => setDraft(res.messages.length > 1 ? res : null))
      .catch(() => setDraft(null));
  }, [token]);

  if (loading || !user) return null;

  const firstName = user.full_name.split(" ")[0];
  const answered = draft?.progress?.answered ?? 0;
  const remaining = draft?.progress?.remaining_known ?? 0;

  const share = answered + remaining > 0 ? answered / (answered + remaining) : 0;
  const pct = !draft
    ? 0
    : draft.stage === "complete"
      ? 80
      : draft.product_code
        ? 10 + Math.round(share * 70)
        : draft.stage === "product_selection"
          ? 5
          : 0;
  const preview = draft ? lastAgentLine(draft) : null;

  return (
    <div className="min-h-dvh bg-slate-50 text-slate-900" style={THEME}>
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex h-14 max-w-4xl items-center justify-between px-4 sm:h-16 sm:px-6">
          <span className="flex items-center gap-2 text-lg font-semibold text-primary">
            <Landmark className="h-5 w-5" aria-hidden="true" />
            Loan Assistant
          </span>
          <div className="flex items-center gap-3">
            <span className="hidden text-sm text-slate-500 sm:inline">{user.full_name}</span>
            <button
              type="button"
              onClick={logout}
              className="inline-flex items-center gap-1.5 rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 transition-colors hover:border-primary hover:text-primary"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              Log out
            </button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-4 py-8 sm:px-6 lg:py-10">
        <h1 className="text-2xl font-semibold tracking-tight">Welcome back, {firstName}</h1>
        <p className="mt-1 text-sm text-slate-500">Apply for a loan, pick up where you left off, and track your applications.</p>

        {draft ? (
          <section className="chat-in mt-6 overflow-hidden rounded-xl border border-primary/20 bg-white shadow-sm">
            <div className="flex flex-col gap-4 p-5 sm:flex-row sm:items-center sm:justify-between sm:p-6">
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold uppercase tracking-wide text-primary">Application in progress</p>
                <h2 className="mt-1 text-lg font-semibold">Continue where you left off</h2>
                {preview && (
                  <p className="mt-2 line-clamp-2 border-l-2 border-primary/30 pl-3 text-sm italic text-slate-500">
                    {preview}
                  </p>
                )}
                {pct > 0 && (
                  <div className="mt-4 max-w-sm">
                    <div className="flex justify-between text-xs text-slate-500">
                      <span>{answered} {answered === 1 ? "answer" : "answers"} so far</span>
                      <span>{pct}%</span>
                    </div>
                    <div className="mt-1 h-1.5 overflow-hidden rounded-full bg-slate-100">
                      <div className="h-full rounded-full bg-primary transition-all" style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )}
              </div>
              <Link
                href="/customer/chat"
                className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-md bg-primary px-5 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90"
              >
                Continue
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
          </section>
        ) : (
          <section className="chat-in mt-6 overflow-hidden rounded-xl bg-primary text-primary-foreground shadow-sm">
            <div className="flex flex-col gap-5 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-8">
              <div>
                <h2 className="text-xl font-semibold">Ready to apply for a loan?</h2>
                <p className="mt-1 max-w-lg text-sm text-white/80">
                  Our assistant asks one question at a time, checks your documents, and sends your application to the
                  bank when you&apos;re ready. Your answers are saved as you go.
                </p>
              </div>
              <Link
                href="/customer/chat"
                className="inline-flex h-10 shrink-0 items-center justify-center gap-2 rounded-md bg-white px-5 text-sm font-medium text-primary shadow-sm transition-colors hover:bg-white/90"
              >
                Start application
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </Link>
            </div>
          </section>
        )}

        <div className="mt-6 grid gap-3 sm:grid-cols-3">
          {[
            { icon: MessageSquare, title: "Chat, don't fill forms", text: "Answer in your own words." },
            { icon: ShieldCheck, title: "Saved automatically", text: "Leave any time and come back." },
            { icon: UserCheck, title: "Reviewed by a person", text: "Every decision is made by the bank's team." },
          ].map(({ icon: Icon, title, text }) => (
            <div key={title} className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-4">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Icon className="h-4 w-4" aria-hidden="true" />
              </span>
              <div>
                <p className="text-sm font-semibold">{title}</p>
                <p className="mt-0.5 text-xs text-slate-500">{text}</p>
              </div>
            </div>
          ))}
        </div>

        <section className="mt-8 rounded-xl border border-slate-200 bg-white">
          <div className="flex items-center justify-between border-b border-slate-200 px-5 py-4">
            <h2 className="font-semibold">My applications</h2>
            <span className="text-xs text-slate-400">{applications.length} total</span>
          </div>
          {appsLoading ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 2 }).map((_, i) => (
                <div key={i} className="h-16 animate-pulse rounded-lg bg-slate-100" />
              ))}
            </div>
          ) : applications.length === 0 ? (
            <div className="flex flex-col items-center gap-2 px-4 py-14 text-center">
              <FileText className="h-8 w-8 text-slate-300" aria-hidden="true" />
              <p className="text-sm text-slate-400">No submitted applications yet.</p>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100">
              {applications.map((a) => {
                const s = STATUS[a.status] ?? STATUS.submitted;
                const Icon = s.icon;
                return (
                  <li key={a.id} className="flex items-center justify-between gap-3 px-5 py-4">
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-500">
                        <FileText className="h-5 w-5" aria-hidden="true" />
                      </span>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">
                          {a.product_name ?? <span className="capitalize">{a.loan_type} loan</span>}
                        </p>
                        <p className="mt-0.5 text-xs text-slate-500">
                          {money(a.requested_amount)}
                          {a.tenure_requested_months ? ` · ${a.tenure_requested_months} months` : ""} ·{" "}
                          {new Date(a.created_at).toLocaleDateString("en-AU", { day: "numeric", month: "short", year: "numeric" })}
                        </p>
                        {a.status === "under_review" && a.pending_position_title && (
                          <p className="mt-0.5 text-xs text-slate-400">With the {a.pending_position_title}</p>
                        )}
                      </div>
                    </div>
                    <span
                      className={cn(
                        "inline-flex shrink-0 items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium",
                        s.className,
                      )}
                    >
                      <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                      {s.label}
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}
