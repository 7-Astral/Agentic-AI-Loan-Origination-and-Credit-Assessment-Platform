"use client";

import { useEffect, useMemo, useState } from "react";
import { api, type ChatReport, type ChatReportDocument } from "@/lib/api";
import { fmtAnswer, fmtDateTime, humanize } from "./format";


const CHECK_STYLE: Record<
  string,
  { label: string; text: string; box: string; row: string }
> = {
  match: {
    label: "Match",
    text: "text-[#2e844a]",
    box: "border-[#2e844a] bg-[#2e844a]/15",
    row: "border-l-[#2e844a]",
  },
  mismatch: {
    label: "Mismatch",
    text: "text-[#8c5a00]",
    box: "border-[#c9a227] bg-[#c9a227]/25",
    row: "border-l-[#c9a227] bg-[#fdf6e7]",
  },
  missing: {
    label: "Not found",
    text: "text-[#5d6470]",
    box: "border-[#8a909a] bg-[#8a909a]/15",
    row: "border-l-[#b0b6bf]",
  },
  on_file: {
    label: "On file",
    text: "text-[#5d6470]",
    box: "border-[#8a909a] bg-[#8a909a]/15",
    row: "border-l-[#b0b6bf]",
  },
};

const DOC_STATUS: Record<string, { label: string; className: string }> = {
  extracted: { label: "Read", className: "text-[#2e844a]" },
  needs_reupload: { label: "Needs re-upload", className: "text-[#c23934]" },
  uploaded: { label: "Processing", className: "text-[#5d6470]" },
};

function docChecks(doc: ChatReportDocument) {
  return doc.verifications.filter((v) => v.slot_id);
}

function useDocumentUrl(
  token: string | null,
  applicationId: string,
  doc: ChatReportDocument | undefined,
  enabled: boolean,
) {
  const [url, setUrl] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    if (!token || !doc || !enabled) return;
    let objectUrl: string | null = null;
    let cancelled = false;
    setUrl(null);
    setFailed(false);
    api
      .bankDocumentFile(token, applicationId, doc.document_id)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      })
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [token, applicationId, doc, enabled]);
  return { url, failed };
}

export function VerificationWorkspace({
  chat,
  token,
  applicationId,
  active = true,
}: {
  chat: ChatReport;
  token: string | null;
  applicationId: string;
  active?: boolean;
}) {
  const [docId, setDocId] = useState(chat.documents[0]?.document_id);
  const doc =
    chat.documents.find((d) => d.document_id === docId) ?? chat.documents[0];
  const [field, setField] = useState<string | null>(null);
  const [opened, setOpened] = useState(active);
  useEffect(() => {
    if (active) setOpened(true);
  }, [active]);
  const { url, failed } = useDocumentUrl(token, applicationId, doc, opened);

  const allChecks = chat.documents.flatMap(docChecks);
  const matched = allChecks.filter((v) => v.status === "match").length;
  const mismatched = allChecks.filter((v) => v.status === "mismatch").length;

  
  useEffect(() => {
    setField(
      doc
        ? (docChecks(doc).find((v) => v.status === "mismatch")
            ?.extracted_field ??
            docChecks(doc)[0]?.extracted_field ??
            null)
        : null,
    );
  }, [doc]);

  const extracted = useMemo(
    () =>
      Object.entries(doc?.extraction?.extracted_fields ?? {}).filter(
        ([key]) => key !== "transactions",
      ),
    [doc],
  );
  const transactions = doc?.extraction?.extracted_fields?.transactions;

  if (chat.documents.length === 0) {
    return (
      <div className="px-4 py-12 text-center">
        <p className="text-[14px] text-[#1b1e23]">No documents uploaded yet.</p>
        <p className="mt-1 text-[13px] text-[#8a909a]">
          Documents the applicant uploads in the chat appear here for
          verification.
        </p>
      </div>
    );
  }

  const checkFor = (fieldName: string) =>
    docChecks(doc).find((v) => v.extracted_field === fieldName);
  const isPdf = doc.content_type === "application/pdf";

  return (
    <div>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-[#e3e6ea] px-4 py-3 text-[13px]">
        <span className="font-semibold text-[#1b1e23]">Verification</span>
        <span className="text-[#343a42]">
          {chat.documents.length} document
          {chat.documents.length === 1 ? "" : "s"}
        </span>
        <span className="text-[#2e844a]">✓ {matched} matched</span>
        <span className={mismatched ? "text-[#8c5a00]" : "text-[#8a909a]"}>
          ⚠ {mismatched} mismatch{mismatched === 1 ? "" : "es"}
        </span>
        <div className="ml-auto flex min-w-[160px] flex-1 items-center gap-2 sm:max-w-[240px]">
          <div className="h-1.5 flex-1 bg-[#e5e8ec]">
            <div
              className="h-full bg-[#2e844a]"
              style={{
                width: `${allChecks.length ? (matched / allChecks.length) * 100 : 0}%`,
              }}
            />
          </div>
          <span className="text-[12px] text-[#5d6470]">
            {matched}/{allChecks.length} verified
          </span>
        </div>
      </div>

      <div>
        {/* Document picker */}
        <ul className="grid grid-cols-1 border-b border-[#e3e6ea] sm:grid-cols-2 xl:grid-cols-3 print:hidden">
          {chat.documents.map((d) => {
            const checks = docChecks(d);
            const bad = checks.filter((v) => v.status === "mismatch").length;
            const status = DOC_STATUS[d.status] ?? {
              label: humanize(d.status),
              className: "text-[#5d6470]",
            };
            const selected = d.document_id === doc.document_id;
            return (
              <li key={d.document_id}>
                <button
                  type="button"
                  onClick={() => setDocId(d.document_id)}
                  aria-pressed={selected}
                  className={`h-full w-full border-b-[3px] border-r border-r-[#e3e6ea] px-4 py-3 text-left transition-colors ${
                    selected
                      ? "border-b-[#1f5fa8] bg-[#f3f6fa]"
                      : "border-b-transparent hover:bg-[#f7f8fa]"
                  }`}
                >
                  <p className="text-[14px] font-medium text-[#1b1e23]">
                    {humanize(d.verification_type)}
                  </p>
                  <p className="truncate text-[12px] text-[#8a909a]">
                    {d.original_filename}
                  </p>
                  <p className="mt-1 flex gap-3 text-[12px]">
                    <span className={status.className}>{status.label}</span>
                    {checks.length > 0 && (
                      <span
                        className={bad ? "text-[#8c5a00]" : "text-[#2e844a]"}
                      >
                        {bad
                          ? `${bad} mismatch${bad === 1 ? "" : "es"}`
                          : "All checks match"}
                      </span>
                    )}
                  </p>
                </button>
              </li>
            );
          })}
        </ul>

        <div>
          {/* Viewer */}
          <div className="min-w-0 border-b border-[#e3e6ea] bg-[#eceef1] p-4">
            <p className="mb-2 flex items-center justify-between gap-2 text-[12px] text-[#5d6470]">
              <span className="truncate">{doc.original_filename}</span>
              <span className="shrink-0">
                Uploaded {fmtDateTime(doc.uploaded_at)}
              </span>
            </p>
            <div className="relative mx-auto max-w-[640px] border border-[#d6d9de] bg-white shadow-sm">
              {failed ? (
                <p className="px-4 py-16 text-center text-[13px] text-[#8a909a]">
                  The file couldn&apos;t be loaded.
                </p>
              ) : !url ? (
                <p className="px-4 py-16 text-center text-[13px] text-[#8a909a]">
                  Loading document…
                </p>
              ) : isPdf ? (
                <iframe
                  src={url}
                  title={doc.original_filename}
                  className="h-[640px] w-full"
                />
              ) : (
                <>
                  {/* eslint-disable-next-line @next/next/no-img-element -- blob URL from an authenticated fetch */}
                  <img
                    src={url}
                    alt={`${humanize(doc.verification_type)} — ${doc.original_filename}`}
                    className="block w-full"
                  />
                  {doc.layout &&
                    Object.entries(doc.layout.fields).map(([name, box]) => {
                      const check = checkFor(name);
                      const active = name === field;
                      const style = check
                        ? (CHECK_STYLE[check.status] ?? CHECK_STYLE.on_file)
                        : null;
                      return (
                        <button
                          key={name}
                          type="button"
                          title={humanize(name)}
                          aria-label={`Highlight ${humanize(name)}`}
                          onClick={() => setField(name)}
                          className={`absolute border-2 transition-all ${
                            active
                              ? `${style?.box ?? "border-[#1f5fa8] bg-[#1f5fa8]/15"} ring-4 ring-white/60`
                              : "border-[#1f5fa8]/25 bg-transparent hover:border-[#1f5fa8]/60"
                          }`}
                          style={{
                            left: `${((box.x - 3) / doc.layout!.width) * 100}%`,
                            top: `${((box.y - 3) / doc.layout!.height) * 100}%`,
                            width: `${((box.w + 6) / doc.layout!.width) * 100}%`,
                            height: `${((box.h + 6) / doc.layout!.height) * 100}%`,
                          }}
                        />
                      );
                    })}
                </>
              )}
            </div>
            {!doc.layout && url && !isPdf && (
              <p className="mt-2 text-center text-[12px] text-[#8a909a]">
                Field positions aren&apos;t available for this document.
              </p>
            )}
          </div>

          {/* Checks and extracted fields */}
          <div className="grid grid-cols-1 md:grid-cols-2">
            <div className="md:border-r md:border-[#e3e6ea]">
              <h3 className="border-b border-[#e3e6ea] px-4 py-3 text-[14px] font-semibold text-[#1b1e23]">
                Checks
              </h3>
              {docChecks(doc).length === 0 ? (
                <p className="px-4 py-3 text-[13px] text-[#8a909a]">
                  No declared answers to compare for this document.
                </p>
              ) : (
                <ul>
                  {docChecks(doc).map((v, i) => {
                    const style = CHECK_STYLE[v.status] ?? CHECK_STYLE.on_file;
                    const active =
                      v.extracted_field && v.extracted_field === field;
                    return (
                      <li key={i}>
                        <button
                          type="button"
                          onClick={() =>
                            v.extracted_field && setField(v.extracted_field)
                          }
                          className={`w-full border-b border-l-[3px] border-b-[#e3e6ea] px-4 py-3 text-left ${style.row} ${active ? "outline outline-2 -outline-offset-2 outline-[#1f5fa8]/40" : ""}`}
                        >
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-[13px] font-medium text-[#1b1e23]">
                              {humanize(v.slot_id)}
                            </span>
                            <span
                              className={`text-[12px] font-semibold ${style.text}`}
                            >
                              {style.label}
                            </span>
                          </div>
                          <dl className="mt-1.5 space-y-0.5 text-[12px]">
                            <div className="flex gap-2">
                              <dt className="w-[70px] shrink-0 text-[#8a909a]">
                                Declared
                              </dt>
                              <dd className="text-[#1b1e23]">
                                {v.declared_value || "—"}
                              </dd>
                            </div>
                            <div className="flex gap-2">
                              <dt className="w-[70px] shrink-0 text-[#8a909a]">
                                Document
                              </dt>
                              <dd className="text-[#1b1e23]">
                                {v.extracted_value || "—"}
                              </dd>
                            </div>
                          </dl>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
            <div>
              <h3 className="border-b border-[#e3e6ea] px-4 py-3 text-[14px] font-semibold text-[#1b1e23]">
                Read from the document
              </h3>
              <div>
                {extracted.map(([key, value]) => (
                  <button
                    key={key}
                    type="button"
                    onClick={() => setField(key)}
                    disabled={!doc.layout?.fields[key]}
                    className={`flex w-full items-baseline justify-between gap-3 border-b border-[#e3e6ea] px-4 py-2 text-left text-[13px] enabled:hover:bg-[#f7f8fa] ${
                      key === field ? "bg-[#f3f6fa]" : ""
                    }`}
                  >
                    <span className="text-[#5d6470]">{humanize(key)}</span>
                    <span className="text-right text-[#1b1e23]">
                      {fmtAnswer(
                        value,
                        typeof value === "number" ? "currency" : null,
                      )}
                    </span>
                  </button>
                ))}
                {Array.isArray(transactions) && (
                  <div className="flex justify-between border-b border-[#e3e6ea] px-4 py-2 text-[13px]">
                    <span className="text-[#5d6470]">Transactions</span>
                    <span className="text-[#1b1e23]">
                      {transactions.length} read
                    </span>
                  </div>
                )}
                {doc.extraction?.notes && (
                  <p className="px-4 py-2 text-[12px] text-[#8a909a]">
                    {doc.extraction.notes}
                  </p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
