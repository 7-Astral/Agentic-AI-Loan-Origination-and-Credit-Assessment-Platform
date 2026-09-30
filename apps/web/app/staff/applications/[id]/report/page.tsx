"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { api, type AssessmentReport, type ChatReport, type LoanApplicationOut, ApiError } from "@/lib/api";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Skeleton } from "@/components/ui/Skeleton";
import { IconFile, IconSparkle } from "@/components/icons";
import { DecideModal } from "@/components/applications/DecideModal";
import {
  ApplicantPanel,
  AssessmentPanel,
  AttentionPanel,
  ConversationPanel,
  DocumentsPanel,
  NarrativePanel,
  SummaryTiles,
} from "@/components/reports/ReportSections";
import { STATUS_TONE, fmtDate, fmtDateTime, fmtMoney, statusLabel } from "@/components/reports/format";

// Application report for a chat-originated application. Answer first: who,
// how much, what the assessment recommends and what needs attention, with the
// Decide action beside it; the evidence (Five C's detail, interview answers,
// documents, conversation) sits in tabs. Printing shows every tab — the
// layout's print:hidden classes drop the portal chrome.

type TabId = "assessment" | "applicant" | "documents" | "conversation";

export default function ApplicationReportPage() {
  const params = useParams<{ id: string }>();
  const { token, user } = useAuth();
  const [application, setApplication] = useState<LoanApplicationOut | null>(null);
  const [chat, setChat] = useState<ChatReport | null>(null);
  const [assessment, setAssessment] = useState<AssessmentReport | null>(null);
  const [assessmentNote, setAssessmentNote] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<TabId>("assessment");
  const [deciding, setDeciding] = useState(false);

  const load = useCallback(() => {
    if (!token || !params.id) return;
    setLoading(true);
    Promise.allSettled([
      api.bankApplications(token).then((apps) => setApplication(apps.find((a) => a.id === params.id) ?? null)),
      api.bankChatReport(token, params.id).then(setChat),
      // Loaded on its own so a missing assessment never hides the rest of the report.
      api
        .bankAssessmentReport(token, params.id)
        .then(setAssessment)
        .catch((e) => {
          setAssessmentNote(e instanceof ApiError ? e.message : "The assessment couldn't be loaded.");
          throw e;
        }),
    ])
      .then(([, chatResult]) => {
        if (chatResult.status === "rejected") {
          const e = chatResult.reason;
          setError(e instanceof ApiError ? e.message : "Failed to load the report");
        }
      })
      .finally(() => setLoading(false));
  }, [token, params.id]);

  useEffect(load, [load]);

  const facts = new Map(assessment?.applicant_summary.map((f) => [f.id, f.value]) ?? []);
  const applicantName = application?.applicant_name ?? (facts.get("full_name") as string | undefined) ?? "Applicant";
  const termMonths = facts.get("loan_term_months") as number | undefined;
  const creditMetric = chat?.assessment?.metrics.credit_score;
  const creditScore = creditMetric?.state === "computed" && typeof creditMetric.value === "number" ? creditMetric.value : null;

  const tabs: { id: TabId; label: string; count?: number }[] = [
    { id: "assessment", label: "Assessment" },
    { id: "applicant", label: "Applicant" },
    { id: "documents", label: "Documents", count: chat?.documents.length },
    { id: "conversation", label: "Conversation", count: chat?.transcript.length },
  ];

  return (
    <div className="print:mx-0 print:max-w-none">
      <Link
        href="/staff/applications"
        className="inline-flex items-center gap-1 text-xs font-medium text-slate-500 transition-colors hover:text-indigo-700 print:hidden"
      >
        &larr; All applications
      </Link>

      {/* Print-only letterhead, so an exported PDF identifies itself. */}
      <div className="hidden items-center justify-between border-b border-slate-200 pb-3 print:flex">
        <p className="flex items-center gap-2 text-sm font-semibold text-slate-900">
          <IconSparkle className="h-4 w-4" />
          Loan Origination — Application Report
        </p>
        <p className="text-xs text-slate-400">
          Printed {new Date().toLocaleString()}
          {user && ` by ${user.full_name}`}
        </p>
      </div>

      <header className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between print:mt-4">
        <div className="min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Loan application</p>
          {loading && !application ? (
            <Skeleton className="mt-2 h-8 w-64" />
          ) : (
            <h1 className="mt-1 truncate text-2xl font-semibold tracking-tight text-slate-900">{applicantName}</h1>
          )}
          <p className="mt-1 text-sm text-slate-500">
            {[
              assessment?.product_name ?? chat?.product_code,
              application && fmtMoney(application.requested_amount),
              termMonths && `${termMonths} months`,
              application && `submitted ${fmtDate(application.created_at)}`,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
          {application && (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <Badge tone={STATUS_TONE[application.status] ?? "slate"}>{statusLabel(application.status)}</Badge>
              {application.pending_position_title && application.status === "under_review" && (
                <span className="text-xs text-slate-500">Awaiting {application.pending_position_title}</span>
              )}
            </div>
          )}
        </div>
        <div className="flex shrink-0 gap-2 print:hidden">
          <Button variant="secondary" onClick={() => window.print()} disabled={!chat}>
            <IconFile className="h-4 w-4" />
            Print / PDF
          </Button>
          {application?.status === "under_review" && <Button onClick={() => setDeciding(true)}>Decide</Button>}
        </div>
      </header>

      {error && <div className="mt-6 rounded-lg bg-red-50 px-3.5 py-2.5 text-sm text-red-700">{error}</div>}

      {loading && !chat && !error && (
        <div className="mt-6 grid grid-cols-2 gap-3 lg:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-24 rounded-2xl" />
          ))}
        </div>
      )}

      {assessment && (
        <div className="mt-6 space-y-6">
          <SummaryTiles assessment={assessment} creditScore={creditScore} />
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-5">
            <div className="lg:col-span-3">
              <NarrativePanel text={assessment.narrative_summary} />
            </div>
            <div className="lg:col-span-2">
              <AttentionPanel assessment={assessment} />
            </div>
          </div>
        </div>
      )}
      {!loading && !assessment && assessmentNote && (
        <div className="mt-6 rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500">
          Five C&apos;s assessment unavailable: {assessmentNote}
        </div>
      )}

      {chat?.decision && (
        <div className="mt-6 rounded-2xl border border-slate-200/80 bg-white px-5 py-4 text-sm shadow-sm shadow-slate-200/50">
          <p className="font-medium text-slate-900">
            Decision: {statusLabel(chat.decision.outcome)}
            <span className="ml-2 font-normal text-slate-400">{fmtDateTime(chat.decision.decided_at)}</span>
          </p>
          {chat.decision.reasoning && <p className="mt-1 text-slate-600">{chat.decision.reasoning}</p>}
        </div>
      )}

      {chat && (
        <section className="mt-8">
          <Tabs tabs={tabs} active={tab} onChange={setTab} />
          <div className="mt-5 space-y-8">
            <TabPanel id="assessment" active={tab} title="Assessment">
              {assessment ? (
                <AssessmentPanel assessment={assessment} chat={chat} />
              ) : (
                <p className="text-sm text-slate-400">No assessment available.</p>
              )}
            </TabPanel>
            <TabPanel id="applicant" active={tab} title="Applicant">
              <ApplicantPanel chat={chat} />
            </TabPanel>
            <TabPanel id="documents" active={tab} title="Documents">
              <DocumentsPanel chat={chat} />
            </TabPanel>
            <TabPanel id="conversation" active={tab} title="Conversation">
              <ConversationPanel chat={chat} />
            </TabPanel>
          </div>
          <p className="mt-6 text-xs text-slate-400">
            Chat session {chat.session_id}
            {assessment && ` · assessed ${fmtDateTime(assessment.generated_at)}`}
          </p>
        </section>
      )}

      <DecideModal
        application={deciding ? application : null}
        token={token}
        onClose={() => setDeciding(false)}
        onDecided={load}
      />
    </div>
  );
}

function Tabs({ tabs, active, onChange }: {
  tabs: { id: TabId; label: string; count?: number }[];
  active: TabId;
  onChange: (id: TabId) => void;
}) {
  const refs = useRef<Record<string, HTMLButtonElement | null>>({});

  function onKeyDown(e: React.KeyboardEvent, index: number) {
    const step = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
    if (!step) return;
    const next = tabs[(index + step + tabs.length) % tabs.length];
    onChange(next.id);
    refs.current[next.id]?.focus();
  }

  return (
    <div role="tablist" aria-label="Report sections" className="flex gap-1 overflow-x-auto border-b border-slate-200 print:hidden">
      {tabs.map((t, i) => {
        const selected = t.id === active;
        return (
          <button
            key={t.id}
            ref={(el) => {
              refs.current[t.id] = el;
            }}
            type="button"
            role="tab"
            id={`tab-${t.id}`}
            aria-selected={selected}
            aria-controls={`panel-${t.id}`}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(t.id)}
            onKeyDown={(e) => onKeyDown(e, i)}
            className={`-mb-px inline-flex shrink-0 items-center gap-2 border-b-2 px-3 py-2.5 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/40 ${
              selected ? "border-indigo-600 text-indigo-700" : "border-transparent text-slate-500 hover:text-slate-800"
            }`}
          >
            {t.label}
            {t.count !== undefined && (
              <span className={`rounded-full px-1.5 py-0.5 text-[11px] ${selected ? "bg-indigo-50 text-indigo-700" : "bg-slate-100 text-slate-500"}`}>
                {t.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}

function TabPanel({ id, active, title, children }: { id: TabId; active: TabId; title: string; children: React.ReactNode }) {
  return (
    <div
      role="tabpanel"
      id={`panel-${id}`}
      aria-labelledby={`tab-${id}`}
      className={id === active ? "" : "hidden print:block"}
    >
      <h2 className="mb-3 hidden text-base font-semibold text-slate-900 print:block">{title}</h2>
      {children}
    </div>
  );
}
