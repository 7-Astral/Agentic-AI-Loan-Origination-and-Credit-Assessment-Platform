"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api, type LoanApplicationOut, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { IconFile } from "@/components/icons";
import { DecideModal } from "@/components/applications/DecideModal";
import { STATUS_TONE, statusLabel } from "@/components/reports/format";

export default function StaffApplications() {
  const { token } = useAuth();
  const [applications, setApplications] = useState<LoanApplicationOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [decideApp, setDecideApp] = useState<LoanApplicationOut | null>(null);

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
                        <Link
                          href={`/staff/applications/${a.id}/report`}
                          className="inline-flex items-center gap-1.5 rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-medium text-slate-600 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"
                        >
                          <IconFile className="h-3.5 w-3.5" />
                          View report
                        </Link>
                      ) : (
                        <span className="text-xs text-slate-300">Form</span>
                      )}
                    </td>
                    <td className="px-5 py-3.5">
                      {a.status === "under_review" ? (
                        <button
                          type="button"
                          onClick={() => setDecideApp(a)}
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

      <DecideModal
        application={decideApp}
        token={token}
        onClose={() => setDecideApp(null)}
        onDecided={loadApplications}
      />
    </div>
  );
}
