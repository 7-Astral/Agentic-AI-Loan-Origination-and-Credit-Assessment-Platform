"use client";

import { useState, type FormEvent } from "react";
import { Check, Loader2, Paperclip, Send, UserCheck } from "lucide-react";
import type { InfoRequest } from "@/lib/agent-api";

function time(value: string) {
  return new Date(value).toLocaleString("en-AU", {
    day: "numeric",
    month: "short",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function InfoRequestCard({
  request,
  onReply,
  onFile,
}: {
  request: InfoRequest;
  onReply: (message: string) => Promise<void>;
  onFile: (file: File) => Promise<string | null>;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const open = request.status === "open";
  const wanted = request.document_name ?? "document";

  async function submitReply(e: FormEvent) {
    e.preventDefault();
    if (!text.trim() || busy) return;
    setBusy(true);
    setProblem(null);
    try {
      await onReply(text.trim());
      setText("");
    } catch {
      setProblem("That didn't send — please try again.");
    } finally {
      setBusy(false);
    }
  }

  async function submitFile(file: File) {
    setBusy(true);
    setProblem(null);
    try {
      setProblem(await onFile(file));
    } catch {
      setProblem("The upload didn't go through — please try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat-in space-y-3">
      <div className="flex gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-600 text-white">
          <UserCheck className="h-5 w-5" aria-hidden="true" />
        </span>
        <div className="flex min-w-0 max-w-2xl flex-1 flex-col gap-2">
          <div className="flex flex-wrap items-center gap-2 text-xs">
            <span className="inline-flex items-center rounded-full bg-amber-50 px-2.5 py-0.5 font-semibold uppercase text-amber-800">
              {request.requested_by ?? "Bank team"}
            </span>
            <span className="text-slate-400">{time(request.created_at)}</span>
            {open ? (
              <span className="rounded-full bg-amber-100 px-2 py-0.5 font-medium text-amber-800">
                Needs your reply
              </span>
            ) : (
              <span className="flex items-center gap-1 font-medium text-primary">
                <Check className="h-3.5 w-3.5" aria-hidden="true" />
                Sent to the bank
              </span>
            )}
          </div>
          <div className="whitespace-pre-wrap rounded-lg border border-amber-200 bg-amber-50/60 px-4 py-3 text-sm text-slate-800">
            {request.message}
          </div>

          {open && request.kind === "information" && (
            <form onSubmit={submitReply} className="flex items-end gap-2">
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={2}
                placeholder="Type your reply to the bank…"
                disabled={busy}
                className="w-full resize-none rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm placeholder:text-slate-400 focus-visible:border-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:opacity-50"
              />
              <button
                type="submit"
                aria-label="Send reply"
                disabled={busy || text.trim().length === 0}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
              >
                {busy ? (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                ) : (
                  <Send className="h-4 w-4" aria-hidden="true" />
                )}
              </button>
            </form>
          )}

          {open && request.kind === "document" && (
            <label className="flex cursor-pointer items-center justify-center gap-2 rounded-md border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:border-primary hover:bg-secondary hover:text-primary">
              <input
                type="file"
                accept="image/*,application/pdf"
                className="sr-only"
                disabled={busy}
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) submitFile(file);
                  e.target.value = "";
                }}
              />
              {busy ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Paperclip className="h-4 w-4" aria-hidden="true" />
              )}
              {busy ? "Reading your document…" : `Upload ${wanted}`}
            </label>
          )}

          {problem && <p className="text-sm text-red-600">{problem}</p>}
        </div>
      </div>

      {!open && request.response_text && (
        <div className="flex justify-end">
          <div className="max-w-2xl whitespace-pre-wrap rounded-lg bg-primary px-4 py-3 text-sm text-primary-foreground">
            {request.kind === "document"
              ? `📎 ${request.response_text}`
              : request.response_text}
          </div>
        </div>
      )}
    </div>
  );
}
