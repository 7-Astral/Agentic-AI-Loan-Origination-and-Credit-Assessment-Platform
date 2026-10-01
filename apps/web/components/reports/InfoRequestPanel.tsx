"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { api, ApiError, type ChatReport, type LoanApplicationOut } from "@/lib/api";
import type { InfoRequest } from "@/lib/agent-api";
import { Pill, ui } from "./ReportSections";
import { fmtDateTime, humanize } from "./format";

const OTHER = "other";

export function InfoRequestPanel({
  application,
  chat,
  token,
  onAnswered,
}: {
  application: LoanApplicationOut | null;
  chat: ChatReport;
  token: string | null;
  onAnswered: () => void;
}) {
  const [requests, setRequests] = useState<InfoRequest[]>([]);
  const [kind, setKind] = useState<"information" | "document">("information");
  const [documentCode, setDocumentCode] = useState(OTHER);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const answeredCount = useRef<number | null>(null);

  const applicationId = application?.id;
  const canAsk = application?.status === "under_review" || application?.status === "submitted";
  const documentTypes = Array.from(new Set(chat.documents.map((d) => d.verification_type))).filter(
    (code) => code !== "additional",
  );

  const refresh = useCallback(() => {
    if (!token || !applicationId) return;
    api
      .bankInfoRequests(token, applicationId)
      .then((rows) => {
        const answered = rows.filter((r) => r.status === "answered").length;
        if (answeredCount.current !== null && answered > answeredCount.current) onAnswered();
        answeredCount.current = answered;
        setRequests(rows);
      })
      .catch(() => {});
  }, [token, applicationId, onAnswered]);

  useEffect(() => {
    refresh();
    const timer = setInterval(refresh, 20000);
    return () => clearInterval(timer);
  }, [refresh]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!token || !applicationId || !message.trim() || sending) return;
    setSending(true);
    setError(null);
    try {
      await api.createBankInfoRequest(token, applicationId, {
        kind,
        message: message.trim(),
        document_code: kind === "document" && documentCode !== OTHER ? documentCode : null,
      });
      setMessage("");
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The request couldn't be sent.");
    } finally {
      setSending(false);
    }
  }

  const open = requests.filter((r) => r.status === "open").length;

  return (
    <div className={`${ui.panel} print:hidden`}>
      <div className="flex items-center justify-between gap-3 border-b border-[#e3e6ea] px-4 py-3">
        <h2 className={ui.panelTitle}>Request from applicant</h2>
        {open > 0 && <Pill tone="amber">{open} awaiting reply</Pill>}
      </div>

      {requests.length > 0 && (
        <ol className="divide-y divide-[#e3e6ea]">
          {requests.map((r) => (
            <li key={r.id} className="space-y-1.5 px-4 py-3">
              <div className="flex items-center justify-between gap-2">
                <span className={`text-[12px] ${ui.muted}`}>
                  {r.kind === "document" ? "Document" : "Information"} · {fmtDateTime(r.created_at)}
                </span>
                <Pill tone={r.status === "open" ? "amber" : "emerald"}>
                  {r.status === "open" ? "Awaiting reply" : "Answered"}
                </Pill>
              </div>
              <p className="whitespace-pre-wrap text-[13px] text-[#343a42]">{r.message}</p>
              {r.status === "answered" && (
                <div className="rounded-[4px] bg-[#f3f6fa] px-3 py-2">
                  <p className={`text-[12px] ${ui.muted}`}>
                    Applicant{r.answered_at ? ` · ${fmtDateTime(r.answered_at)}` : ""}
                  </p>
                  <p className="whitespace-pre-wrap text-[13px] text-[#1b1e23]">
                    {r.kind === "document"
                      ? `Uploaded ${r.response_text ?? "a file"} — see the Documents tab`
                      : r.response_text}
                  </p>
                </div>
              )}
            </li>
          ))}
        </ol>
      )}

      {canAsk ? (
        <form onSubmit={submit} className={`space-y-3 px-4 py-3 ${requests.length > 0 ? "border-t border-[#e3e6ea]" : ""}`}>
          <div className="flex gap-4 text-[13px] text-[#343a42]">
            {(["information", "document"] as const).map((k) => (
              <label key={k} className="flex cursor-pointer items-center gap-1.5">
                <input
                  type="radio"
                  name="info-request-kind"
                  checked={kind === k}
                  onChange={() => setKind(k)}
                  className="accent-[#1f5fa8]"
                />
                {k === "information" ? "Ask a question" : "Ask for a document"}
              </label>
            ))}
          </div>

          {kind === "document" && (
            <div>
              <label htmlFor="info-request-document" className={ui.label}>
                Document type
              </label>
              <select
                id="info-request-document"
                value={documentCode}
                onChange={(e) => setDocumentCode(e.target.value)}
                className="mt-1 w-full rounded-[4px] border border-[#cfd3d9] bg-white px-2.5 py-1.5 text-[13px] text-[#1b1e23] focus:border-[#1f5fa8] focus:outline-none"
              >
                <option value={OTHER}>Other document</option>
                {documentTypes.map((code) => (
                  <option key={code} value={code}>
                    {humanize(code)} (new copy)
                  </option>
                ))}
              </select>
            </div>
          )}

          <div>
            <label htmlFor="info-request-message" className={ui.label}>
              Message to the applicant
            </label>
            <textarea
              id="info-request-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              rows={3}
              maxLength={2000}
              placeholder={
                kind === "document"
                  ? "Say which document you need and why"
                  : "Write your question for the applicant"
              }
              className="mt-1 w-full resize-none rounded-[4px] border border-[#cfd3d9] bg-white px-2.5 py-2 text-[13px] text-[#1b1e23] placeholder:text-[#8a909a] focus:border-[#1f5fa8] focus:outline-none"
            />
          </div>

          {error && <p className="text-[13px] text-[#c23934]">{error}</p>}

          <button type="submit" disabled={sending || message.trim().length === 0} className={`${ui.brandButton} w-full`}>
            {sending ? "Sending…" : "Send to applicant"}
          </button>
          <p className={`text-[12px] ${ui.muted}`}>
            The applicant is notified and replies from their application chat.
          </p>
        </form>
      ) : (
        requests.length === 0 && (
          <p className={`px-4 py-3 text-[13px] ${ui.muted}`}>No requests were sent for this application.</p>
        )
      )}
    </div>
  );
}
