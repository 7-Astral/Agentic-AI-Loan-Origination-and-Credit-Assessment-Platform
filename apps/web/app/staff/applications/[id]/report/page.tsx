"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { IBM_Plex_Sans } from "next/font/google";
import { useAuth } from "@/lib/auth-context";
import {
  api,
  type AssessmentReport,
  type ChatReport,
  type LoanApplicationOut,
  ApiError,
} from "@/lib/api";
import { DecideModal } from "@/components/applications/DecideModal";
import { VerificationWorkspace } from "@/components/reports/VerificationWorkspace";
import {
  ApplicantTab,
  ApprovalPanel,
  ConditionsPanel,
  ConversationTab,
  CreditAssessmentTab,
  RecommendationPanel,
  RecordHeader,
  RecordTabs,
  StageBar,
  ui,
} from "@/components/reports/ReportSections";

const plex = IBM_Plex_Sans({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

type TabId = "assessment" | "applicant" | "documents" | "conversation";

export default function ApplicationReportPage() {
  const params = useParams<{ id: string }>();
  const { token, user } = useAuth();
  const [application, setApplication] = useState<LoanApplicationOut | null>(
    null,
  );
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
      api
        .bankApplications(token)
        .then((apps) =>
          setApplication(apps.find((a) => a.id === params.id) ?? null),
        ),
      api.bankChatReport(token, params.id).then(setChat),
      api
        .bankAssessmentReport(token, params.id)
        .then(setAssessment)
        .catch((e) => {
          setAssessmentNote(
            e instanceof ApiError
              ? e.message
              : "The assessment couldn't be loaded.",
          );
          throw e;
        }),
    ])
      .then(([, chatResult]) => {
        if (chatResult.status === "rejected") {
          const e = chatResult.reason;
          setError(
            e instanceof ApiError ? e.message : "Failed to load the report",
          );
        }
      })
      .finally(() => setLoading(false));
  }, [token, params.id]);

  useEffect(load, [load]);

 
  const needsNarrative = !!assessment && !assessment.narrative_summary;
  useEffect(() => {
    if (!needsNarrative || !token || !params.id) return;
    let cancelled = false;
    api
      .bankAssessmentNarrative(token, params.id)
      .then(
        (res) =>
          !cancelled &&
          setAssessment((a) =>
            a ? { ...a, narrative_summary: res.narrative_summary } : a,
          ),
      )
      .catch(
        () =>
          !cancelled &&
          setAssessment((a) =>
            a
              ? {
                  ...a,
                  narrative_summary:
                    "A written summary isn't available right now — see the scores below.",
                }
              : a,
          ),
      );
    return () => {
      cancelled = true;
    };
  }, [needsNarrative, token, params.id]);

  const fullName = assessment?.applicant_summary.find(
    (f) => f.id === "full_name",
  )?.value as string | undefined;
 
  const applicantName = fullName ?? application?.applicant_name ?? "Applicant";
  const creditMetric = chat?.assessment?.metrics.credit_score;
  const creditScore =
    creditMetric?.state === "computed" && typeof creditMetric.value === "number"
      ? creditMetric.value
      : null;

  const tabs: { id: TabId; label: string; count?: number }[] = [
    { id: "assessment", label: "Credit assessment" },
    { id: "applicant", label: "Applicant details" },
    { id: "documents", label: "Documents", count: chat?.documents.length },
    {
      id: "conversation",
      label: "Conversation",
      count: chat?.transcript.length,
    },
  ];

  return (
    <div
      className={`${plex.className} -m-4 min-h-screen bg-[#eceef1] p-4 text-[#1b1e23] antialiased sm:-m-6 sm:p-6 lg:-m-10 lg:p-8 print:m-0 print:bg-white print:p-0`}
    >
      <div className="mb-3 flex items-center justify-between text-[13px] print:hidden">
        <Link
          href="/staff/applications"
          className="text-[#1f5fa8] hover:underline"
        >
          ‹ Loan applications
        </Link>
      </div>

      <div className="mb-3 hidden justify-between border-b border-[#d6d9de] pb-2 text-[12px] print:flex">
        <span className="font-semibold">
          Loan Origination — Application Report
        </span>
        <span className="text-[#5d6470]">
          Printed {new Date().toLocaleString("en-AU")}
          {user && ` by ${user.full_name}`}
        </span>
      </div>

      <div className="space-y-3">
        <RecordHeader
          applicantName={applicantName}
          accountName={application?.applicant_name}
          application={application}
          assessment={assessment}
          chat={chat}
          actions={
            <>
              {application?.status === "under_review" && (
                <button
                  type="button"
                  className={ui.outlineButton}
                  onClick={() => setDeciding(true)}
                >
                  Record decision
                </button>
              )}
              <button
                type="button"
                className={ui.outlineButton}
                onClick={() => window.print()}
                disabled={!chat}
              >
                Print / PDF
              </button>
            </>
          }
        />
        <StageBar application={application} chat={chat} />

        {error && (
          <div className="rounded-[4px] border border-[#f0c2bf] bg-[#fbe9e8] px-4 py-3 text-[14px] text-[#c23934]">
            {error}
          </div>
        )}
        {loading && !chat && !error && (
          <div
            className={`${ui.panel} px-4 py-10 text-center text-[14px] text-[#8a909a]`}
          >
            Loading report…
          </div>
        )}

        {chat && (
          <div className="flex flex-col gap-3 lg:flex-row lg:items-start print:flex-col">
            <div className={`${ui.panel} min-w-0 flex-1 print:w-full`}>
              <RecordTabs tabs={tabs} active={tab} onChange={setTab} />
              <TabPanel id="assessment" active={tab} title="Credit assessment">
                {assessment ? (
                  <CreditAssessmentTab
                    assessment={assessment}
                    chat={chat}
                    creditScore={creditScore}
                  />
                ) : (
                  <p className="p-4 text-[14px] text-[#8a909a]">
                    Five C&apos;s assessment unavailable
                    {assessmentNote ? `: ${assessmentNote}` : "."}
                  </p>
                )}
              </TabPanel>
              <TabPanel id="applicant" active={tab} title="Applicant details">
                <ApplicantTab chat={chat} />
              </TabPanel>
              <TabPanel id="documents" active={tab} title="Documents">
                <VerificationWorkspace
                  chat={chat}
                  token={token}
                  applicationId={params.id}
                  active={tab === "documents"}
                />
              </TabPanel>
              <TabPanel id="conversation" active={tab} title="Conversation">
                <ConversationTab chat={chat} />
              </TabPanel>
            </div>

            <aside className="w-full shrink-0 space-y-3 lg:sticky lg:top-4 lg:w-[360px] print:order-first print:w-full">
              {assessment && <RecommendationPanel assessment={assessment} />}
              {assessment && <ConditionsPanel assessment={assessment} />}
              <ApprovalPanel
                application={application}
                assessment={assessment}
                chat={chat}
                onDecide={() => setDeciding(true)}
              />
            </aside>
          </div>
        )}

        {chat && (
          <p className="text-[12px] text-[#8a909a]">
            Chat session {chat.session_id}
          </p>
        )}
      </div>

      <DecideModal
        application={deciding ? application : null}
        token={token}
        onClose={() => setDeciding(false)}
        onDecided={load}
      />
    </div>
  );
}

function TabPanel({
  id,
  active,
  title,
  children,
}: {
  id: TabId;
  active: TabId;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div
      role="tabpanel"
      id={`panel-${id}`}
      aria-labelledby={`tab-${id}`}
      className={
        id === active
          ? ""
          : "hidden print:block print:border-t print:border-[#d6d9de]"
      }
    >
      <h2 className="hidden px-4 pt-4 text-[16px] font-semibold print:block">
        {title}
      </h2>
      {children}
    </div>
  );
}
