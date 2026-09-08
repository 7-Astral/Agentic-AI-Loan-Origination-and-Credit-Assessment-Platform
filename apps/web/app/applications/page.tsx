"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertTriangle, FileQuestion, Landmark, Loader2, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { deleteApplication, listConversations } from "@/lib/api";
import type { ConversationSummary } from "@/lib/types/conversation";

type PageState = "loading" | "error" | "ready";

function statusBadgeVariant(status: ConversationSummary["status"]): "success" | "muted" {
  return status === "completed" ? "success" : "muted";
}

export default function ApplicationsPage() {
  const [pageState, setPageState] = useState<PageState>("loading");
  const [applications, setApplications] = useState<ConversationSummary[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    listConversations()
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

  async function handleDelete(id: string) {
    if (!window.confirm("Delete this application? It will no longer appear in this list.")) {
      return;
    }

    setDeletingId(id);
    try {
      await deleteApplication(id);
      setApplications((prev) => prev.filter((application) => application.id !== id));
    } catch {
      window.alert("Couldn't delete this application. Please try again.");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <div className="mx-auto w-full max-w-4xl p-4 sm:p-6">
      <header className="mb-6 flex items-center gap-2">
        <Landmark className="h-5 w-5 text-primary" aria-hidden="true" />
        <h1 className="text-lg font-semibold">Applications</h1>
      </header>

      {pageState === "loading" && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border p-10 text-center text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin" aria-hidden="true" />
          <p className="text-sm">Loading applications...</p>
        </div>
      )}

      {pageState === "error" && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-border p-10 text-center">
          <AlertTriangle className="h-6 w-6 text-amber-600" aria-hidden="true" />
          <p className="text-sm font-medium">Couldn&apos;t load applications. Please try again.</p>
        </div>
      )}

      {pageState === "ready" && applications.length === 0 && (
        <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-dashed border-border p-10 text-center text-muted-foreground">
          <FileQuestion className="h-6 w-6" aria-hidden="true" />
          <p className="text-sm">No applications yet.</p>
        </div>
      )}

      {pageState === "ready" && applications.length > 0 && (
        <ul className="flex flex-col gap-2">
          {applications.map((application) => (
            <li
              key={application.id}
              className="flex items-stretch gap-1 rounded-lg border border-border transition-colors hover:border-primary"
            >
              <Link
                href={`/applications/${application.id}`}
                className="flex flex-1 flex-wrap items-center justify-between gap-3 p-4 hover:bg-secondary/50"
              >
                <div className="flex flex-col gap-1">
                  <span className="font-medium">{application.bank_name}</span>
                  <span className="text-xs text-muted-foreground">
                    {application.selected_loan_type
                      ? `${application.selected_loan_type} loan`
                      : "Loan type not yet selected"}
                    {" · "}
                    {new Date(application.created_at).toLocaleDateString()}
                  </span>
                </div>
                <div className="flex items-center gap-3">
                  {application.total_questions > 0 && (
                    <span className="text-xs text-muted-foreground">
                      {application.current_question_index}/{application.total_questions} questions
                    </span>
                  )}
                  <Badge variant={statusBadgeVariant(application.status)} className="capitalize">
                    {application.status}
                  </Badge>
                </div>
              </Link>
              <button
                type="button"
                onClick={() => void handleDelete(application.id)}
                disabled={deletingId === application.id}
                aria-label="Delete application"
                className="flex items-center px-3 text-muted-foreground hover:text-destructive disabled:opacity-50"
              >
                {deletingId === application.id ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
