"use client";

import { useEffect, useState } from "react";
import { Check, FileText, Upload } from "lucide-react";
import type { RequiredDocument } from "@/lib/agent-api";
import { cn } from "@/lib/utils";

export type DocCardPhase = "waiting" | "reading" | "received" | "rejected" | "skipped";

export type DocCardState = {
  phase: DocCardPhase;
  file?: File;
  reason?: string;
  attempt?: number;
};

export const DOCUMENT_WHY: Record<string, string> = {
  primary_photo_id: "It confirms who you are — a driver licence or passport is perfect.",
  payslip_or_contract: "It confirms your employment and income.",
  payslip_or_tax_return: "It confirms your income.",
  bank_statements: "It shows your everyday income and spending — the last 3 months is ideal.",
  proof_of_address: "It confirms where you live — a recent utility bill or rates notice works.",
  contract_of_sale: "It confirms the purchase price of what you're buying.",
  loan_statement: "It confirms the balance of your existing loan.",
};

export function whyFor(code: string) {
  return DOCUMENT_WHY[code] ?? "The bank needs it to verify your application.";
}

function usePreview(file: File | undefined) {
  const [url, setUrl] = useState<string | null>(null);
  useEffect(() => {
    if (!file || !file.type.startsWith("image/")) {
      setUrl(null);
      return;
    }
    const objectUrl = URL.createObjectURL(file);
    setUrl(objectUrl);
    return () => URL.revokeObjectURL(objectUrl);
  }, [file]);
  return url;
}

function FilePreview({ file, scanning }: { file?: File; scanning: boolean }) {
  const url = usePreview(file);
  return (
    <div className="relative h-36 w-28 shrink-0 overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm">
      {url ? (
        <img src={url} alt="" className="h-full w-full object-cover object-top" />
      ) : (
        <div className="space-y-1.5 p-3" aria-hidden="true">
          <div className="h-2 w-2/3 rounded bg-slate-300" />
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="h-1 rounded bg-slate-200" style={{ width: `${60 + ((i * 37) % 40)}%` }} />
          ))}
        </div>
      )}
      {scanning && (
        <>
          <div className="scan-line scan-line-loop" />
          <div className="absolute inset-0 bg-cyan-500/5" />
        </>
      )}
    </div>
  );
}

export function DocumentRequestCard({
  doc,
  state,
  active,
  onFile,
  onSkip,
}: {
  doc: RequiredDocument;
  state: DocCardState;
  active: boolean;
  onFile: (file: File) => void;
  onSkip: () => void;
}) {
  const [dragOver, setDragOver] = useState(false);
  const { phase } = state;
  const canUpload = active && (phase === "waiting" || phase === "rejected");

  return (
    <div
      key={state.attempt}
      className={cn(
        "chat-in max-w-xl rounded-lg border bg-white p-4 transition-colors",
        phase === "rejected" ? "nudge border-amber-300 bg-amber-50/40" : "border-slate-200",
        phase === "received" && "border-primary/30",
      )}
    >
      <div className="flex items-start gap-3">
        <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-cyan-50 text-cyan-700">
          <FileText className="h-5 w-5" aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-slate-900">{doc.name}</p>
          <p className="text-sm text-slate-500">{whyFor(doc.code)}</p>
        </div>
        {phase === "received" && (
          <span className="flex shrink-0 items-center gap-1 rounded-full bg-secondary px-2.5 py-0.5 text-xs font-semibold text-primary">
            <Check className="h-3.5 w-3.5" aria-hidden="true" /> Received
          </span>
        )}
        {phase === "skipped" && <span className="shrink-0 text-xs text-slate-400">Skipped</span>}
      </div>

      {(phase === "reading" || phase === "received") && (
        <div className="mt-3 flex items-center gap-4">
          <FilePreview file={state.file} scanning={phase === "reading"} />
          <div className="min-w-0 text-sm">
            <p className="truncate font-medium text-slate-800">{state.file?.name}</p>
            {phase === "reading" ? (
              <p className="mt-1 text-slate-500">Reading your document…</p>
            ) : (
              <p className="mt-1 flex items-center gap-1.5 text-primary">
                <Check className="h-4 w-4" aria-hidden="true" /> On file with your application
              </p>
            )}
          </div>
        </div>
      )}

      {phase === "rejected" && state.reason && (
        <p className="mt-3 rounded-md bg-amber-100/70 px-3 py-2 text-sm text-amber-900">{state.reason}</p>
      )}

      {canUpload && (
        <>
          <label
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              e.stopPropagation();
              setDragOver(false);
              const file = e.dataTransfer.files?.[0];
              if (file) onFile(file);
            }}
            className={cn(
              "mt-3 flex cursor-pointer flex-col items-center gap-1.5 rounded-lg border-2 border-dashed px-4 py-5 text-center transition-colors",
              dragOver ? "border-primary bg-secondary" : "border-slate-300 hover:border-primary hover:bg-slate-50",
            )}
          >
            <input
              type="file"
              accept="image/*,application/pdf"
              className="sr-only"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) onFile(file);
                e.target.value = "";
              }}
            />
            <Upload className="h-5 w-5 text-primary" aria-hidden="true" />
            <span className="text-sm font-medium text-slate-800">
              {phase === "rejected" ? "Try another file" : "Drop your file here or choose one"}
            </span>
            <span className="text-xs text-slate-400">A photo or PDF is fine</span>
          </label>
          <button type="button" onClick={onSkip} className="mt-2 text-xs text-slate-500 underline-offset-2 hover:text-slate-800 hover:underline">
            I don&apos;t have this right now — skip
          </button>
        </>
      )}
    </div>
  );
}
