"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { AlertTriangle, ArrowLeft, Loader2, Trash2 } from "lucide-react";

import { RiskReportView } from "@/components/risk-report";
import { Badge } from "@/components/ui/badge";
import { assessRisk, deleteApplication, getConversation, requestFurtherDetails } from "@/lib/api";
import { conversationToApplication } from "@/lib/conversation-to-application";
import type { ConversationState } from "@/lib/types/conversation";
import type { FiveCKey, RiskAssessmentReport } from "@/lib/types/risk-assessment";

type PageState = "loading" | "not-found" | "error" | "ready";

export default function ApplicationDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [pageState, setPageState] = useState<PageState>("loading");
  const [conversation, setConversation] = useState<ConversationState | null>(null);
  const [report, setReport] = useState<RiskAssessmentReport | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [requestingC, setRequestingC] = useState<FiveCKey | null>(null);
  const [requestedCs, setRequestedCs] = useState<Set<FiveCKey>>(new Set());

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setPageState("loading");

      let convo: ConversationState | null;
      try {
        convo = await getConversation(params.id);
      } catch {
        if (!cancelled) setPageState("error");
        return;
      }
      if (cancelled) return;

      if (!convo) {
        setPageState("not-found");
        return;
      }
      setConversation(convo);

      try {
        const application = conversationToApplication(convo);
        const result = await assessRisk(application);
        if (cancelled) return;
        setReport(result);
        setPageState("ready");
      } catch {
        if (!cancelled) setPageState("error");
      }
    }

    void load();
    return () => {
      cancelled = true;
    };
  }, [params.id]);

  async function handleRequestDetails(fiveC: FiveCKey) {
    if (!report) return;

    const missingFields = report.completeness.missing_fields
      .filter((field) => field.five_c === fiveC)
      .map((field) => field.label);

    setRequestingC(fiveC);
    try {
      await requestFurtherDetails(params.id, fiveC, missingFields);
      setRequestedCs((prev) => new Set(prev).add(fiveC));
    } catch {
      window.alert("Couldn't send that request. Please try again.");
    } finally {
      setRequestingC(null);
    }
  }

  async function handleDelete() {
    if (!window.confirm("Delete this application? It will no longer appear in the list.")) {
      return;
    }

    setIsDeleting(true);
    try {
      await deleteApplication(params.id);
      router.push("/applications");
    } catch {
      window.alert("Couldn't delete this application. Please try again.");
      setIsDeleting(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-4xl p-4 sm:p-6">
      <Link
        href="/applications"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to applications
      </Link>

      {conversation && (
        <header className="mb-6 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="text-lg font-semibold">Application risk assessment</h1>
            <Badge variant="outline" className="capitalize">
              {conversation.selected_loan_type ?? "unspecified"} loan
            </Badge>
            <Badge
              variant={conversation.status === "completed" ? "success" : "muted"}
              className="capitalize"
            >
              {conversation.status}
            </Badge>
          </div>
          <button
            type="button"
            onClick={() => void handleDelete()}
            disabled={isDeleting}
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-destructive disabled:opacity-50"
          >
            {isDeleting ? (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            ) : (
              <Trash2 className="h-4 w-4" aria-hidden="true" />
            )}
            Delete application
          </button>
        </header>
      )}

      {pageState === "loading" && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border p-10 text-center text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />
          <p className="text-sm">Assessing application...</p>
        </div>
      )}

      {pageState === "not-found" && (
        <div className="rounded-lg border border-border p-10 text-center">
          <p className="text-sm font-medium">This application couldn&apos;t be found.</p>
        </div>
      )}

      {pageState === "error" && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border p-10 text-center">
          <AlertTriangle className="h-6 w-6 text-amber-600" aria-hidden="true" />
          <p className="text-sm font-medium">
            Couldn&apos;t load the risk assessment. Please try again.
          </p>
        </div>
      )}

      {pageState === "ready" && report && (
        <RiskReportView
          report={report}
          requestDetails={{
            onRequestDetails: (fiveC) => void handleRequestDetails(fiveC),
            requestingC,
            requestedCs,
          }}
        />
      )}
    </div>
  );
}
