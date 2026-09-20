"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { api, type ChatReport, ApiError } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { IconFile, IconSparkle } from "@/components/icons";
import { ChatReportBody } from "@/components/reports/ChatReportBody";

// Standalone, print-friendly rendering of the same chat report shown in the
// "View chat report" modal on staff/applications — opened in its own tab so
// the browser's native Print (Save as PDF) captures just the report, not the
// portal chrome. See the layout's print:hidden classes on the nav/sidebar.
export default function ChatApplicationReportPage() {
  const params = useParams<{ id: string }>();
  const { token, user } = useAuth();
  const [report, setReport] = useState<ChatReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token || !params.id) return;
    api
      .bankChatReport(token, params.id)
      .then(setReport)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load report"))
      .finally(() => setLoading(false));
  }, [token, params.id]);

  return (
    <div className="print:mx-0 print:max-w-none">
      <div className="flex items-start justify-between gap-4 print:hidden">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Chat application report</h1>
          <p className="mt-1 text-sm text-slate-500">
            Printable version — use your browser&apos;s Print dialog and choose &ldquo;Save as PDF&rdquo; to
            download it.
          </p>
        </div>
        <Button onClick={() => window.print()} disabled={!report}>
          <IconFile className="h-4 w-4" />
          Print / Save as PDF
        </Button>
      </div>

      {/* Letterhead — shown on screen and in print, so the exported PDF is self-identifying. */}
      <div className="mt-6 flex items-center justify-between border-b border-slate-200 pb-4 print:mt-0">
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-600 text-white">
            <IconSparkle className="h-4 w-4" />
          </div>
          <div>
            <p className="text-sm font-semibold text-slate-900">Loan Origination — Chat Application Report</p>
            {report && <p className="text-xs text-slate-400">Session {report.session_id}</p>}
          </div>
        </div>
        <div className="text-right text-xs text-slate-400">
          <p>Generated {new Date().toLocaleString()}</p>
          {user && <p>by {user.full_name}</p>}
        </div>
      </div>

      {loading && <p className="mt-6 text-sm text-slate-400">Loading report…</p>}
      {error && <p className="mt-6 text-sm text-red-600">{error}</p>}

      {report && (
        <Card className="mt-6 p-6 print:border-none print:p-0 print:shadow-none">
          <ChatReportBody report={report} />
        </Card>
      )}
    </div>
  );
}
