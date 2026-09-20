"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api, type ChatReport, type LoanApplicationOut, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { IconCheck, IconClose, IconFile, IconMenu } from "@/components/icons";
import { ChatReportBody, statusLabel } from "@/components/reports/ChatReportBody";

const STATUS_TONE: Record<string, "slate" | "indigo" | "emerald" | "amber" | "red"> = {
  draft: "slate",
  submitted: "slate",
  under_review: "amber",
  approved: "emerald",
  rejected: "red",
  disbursed: "indigo",
};

export default function StaffApplications() {
  const { token } = useAuth();
  const { show } = useToast();
  const [applications, setApplications] = useState<LoanApplicationOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [reportOpenFor, setReportOpenFor] = useState<string | null>(null);
  const [report, setReport] = useState<ChatReport | null>(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [reportError, setReportError] = useState<string | null>(null);

  const [decideApp, setDecideApp] = useState<LoanApplicationOut | null>(null);
  const [decideReason, setDecideReason] = useState("");
  const [deciding, setDeciding] = useState<"approved" | "rejected" | null>(null);

  function loadApplications() {
    if (!token) return;
    api
      .bankApplications(token)
      .then(setApplications)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    loadApplications();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  function openReport(applicationId: string) {
    if (!token) return;
    setReportOpenFor(applicationId);
    setReport(null);
    setReportError(null);
    setReportLoading(true);
    api
      .bankChatReport(token, applicationId)
      .then(setReport)
      .catch((e) => setReportError(e instanceof ApiError ? e.message : "Failed to load report"))
      .finally(() => setReportLoading(false));
  }

  function openDecide(app: LoanApplicationOut) {
    setDecideApp(app);
    setDecideReason("");
  }

  async function submitDecision(decision: "approved" | "rejected") {
    if (!token || !decideApp) return;
    setDeciding(decision);
    try {
      await api.decideApplication(token, decideApp.id, { decision, reason: decideReason || undefined });
      show(decision === "approved" ? "Application approved" : "Application rejected", "success");
      setDecideApp(null);
      loadApplications();
    } catch (err) {
      show(err instanceof ApiError ? err.message : "Couldn't record that decision", "error");
    } finally {
      setDeciding(null);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Loan applications</h1>
      <p className="mt-1 text-sm text-slate-500">
        Every application submitted to your bank, with its current status and, if escalated, who needs to
        approve it next.
      </p>

      {error && <div className="mt-4 rounded-lg bg-red-50 px-3.5 py-2.5 text-sm text-red-700">{error}</div>}

      <Card className="mt-6 overflow-hidden">
        <CardHeader title="Applications" subtitle={`${applications.length} total`} />
        {loading ? (
          <TableSkeleton rows={4} cols={4} />
        ) : applications.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-4 py-14 text-center">
            <IconFile className="h-8 w-8 text-slate-300" />
            <p className="text-sm text-slate-400">No applications yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="border-b border-slate-100 bg-slate-50/60 text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-5 py-3 font-medium">Customer</th>
                  <th className="px-5 py-3 font-medium">Type</th>
                  <th className="px-5 py-3 font-medium">Amount</th>
                  <th className="px-5 py-3 font-medium">Status</th>
                  <th className="px-5 py-3 font-medium">Pending on</th>
                  <th className="px-5 py-3 font-medium">Submitted</th>
                  <th className="px-5 py-3 font-medium">Report</th>
                  <th className="px-5 py-3 font-medium">Decision</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {applications.map((a) => (
                  <tr key={a.id} className="transition-colors hover:bg-slate-50/60">
                    <td className="px-5 py-3.5">
                      <p className="font-medium text-slate-800">{a.applicant_name ?? "—"}</p>
                      {a.applicant_email && <p className="text-xs text-slate-400">{a.applicant_email}</p>}
                    </td>
                    <td className="px-5 py-3.5 capitalize text-slate-600">{a.loan_type}</td>
                    <td className="px-5 py-3.5 font-medium text-slate-900">
                      ${a.requested_amount.toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge tone={STATUS_TONE[a.status] ?? "slate"}>{statusLabel(a.status)}</Badge>
                    </td>
                    <td className="px-5 py-3.5 text-slate-600">
                      {a.pending_position_title ?? <span className="text-slate-300">—</span>}
                    </td>
                    <td className="px-5 py-3.5 text-slate-400">
                      {new Date(a.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-5 py-3.5">
                      {a.chat_session_id ? (
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => openReport(a.id)}
                            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
                          >
                            <IconMenu className="h-3.5 w-3.5" />
                            View
                          </button>
                          <a
                            href={`/staff/applications/${a.id}/report`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
                          >
                            <IconFile className="h-3.5 w-3.5" />
                            PDF
                          </a>
                        </div>
                      ) : (
                        <span className="text-xs text-slate-300">Form</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      {a.status === "under_review" ? (
                        <button
                          type="button"
                          onClick={() => openDecide(a)}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700 transition-colors hover:border-amber-300 hover:bg-amber-100"
                        >
                          Decide
                        </button>
                      ) : (
                        <span className="text-xs text-slate-300">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Modal
        open={reportOpenFor !== null}
        onClose={() => setReportOpenFor(null)}
        title="Chat application report"
        widthClassName="sm:max-w-2xl"
      >
        {reportLoading && <p className="text-sm text-slate-400">Loading report…</p>}
        {reportError && <p className="text-sm text-red-600">{reportError}</p>}
        {report && <ChatReportBody report={report} />}
      </Modal>

      <Modal open={decideApp !== null} onClose={() => setDecideApp(null)} title="Decide application">
        {decideApp && (
          <div>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
              <dt className="text-slate-400">Customer</dt>
              <dd className="text-slate-800">{decideApp.applicant_name ?? "—"}</dd>
              <dt className="text-slate-400">Type</dt>
              <dd className="capitalize text-slate-800">{decideApp.loan_type}</dd>
              <dt className="text-slate-400">Amount</dt>
              <dd className="font-medium text-slate-900">${decideApp.requested_amount.toLocaleString()}</dd>
              <dt className="text-slate-400">Pending on</dt>
              <dd className="text-slate-800">{decideApp.pending_position_title ?? "—"}</dd>
            </dl>

            <label className="mt-4 block text-xs font-medium text-slate-500">Reason (optional)</label>
            <textarea
              value={decideReason}
              onChange={(e) => setDecideReason(e.target.value)}
              rows={3}
              placeholder="Notes for the record — shared with the applicant"
              className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-4 focus:ring-indigo-500/10"
            />

            <div className="mt-4 flex gap-2">
              <Button
                onClick={() => submitDecision("approved")}
                loading={deciding === "approved"}
                disabled={deciding !== null}
                className="flex-1"
              >
                <IconCheck className="h-4 w-4" />
                Approve
              </Button>
              <Button
                variant="danger"
                onClick={() => submitDecision("rejected")}
                loading={deciding === "rejected"}
                disabled={deciding !== null}
                className="flex-1"
              >
                <IconClose className="h-4 w-4" />
                Reject
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
