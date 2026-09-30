"use client";

import { FileText, Loader2, ScanLine, Upload } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ScanStage, type ScanPhase, type StagePage } from "@/components/scan/scan-stage";
import { ValuesPanel } from "@/components/scan/values-panel";
import { Button } from "@/components/kit/button";
import { Select } from "@/components/kit/select";
import { extractDocument, getDocumentOptions, sampleDocumentUrl } from "@/lib/playground-api";
import type { Box, DocumentOptions, DocumentSample, ExtractResponse } from "@/lib/types/documents";
import { cn } from "@/lib/utils";

const SWEEP_MS = 2400;
const LOOP_AFTER_MS = SWEEP_MS + 200;
const SEQUENTIAL_MS = 240;
const DEFAULT_UPLOAD_TYPE = "payslip_or_contract";

type Source = { kind: "sample"; sampleId: string } | { kind: "upload"; file: File; verificationType: string };

const blankPage: StagePage = { imageUrl: null, iframeUrl: null, width: 0, height: 0, fields: {}, rows: {} };

function buildPages(
  result: ExtractResponse | null,
  previewUrl: string | null,
  isPdfUpload: boolean,
  sample: DocumentSample | undefined,
): StagePage[] {
  if (result?.pdf_pages && result.pdf_layout) {
    const layout = result.pdf_layout;
    return result.pdf_pages.map((page, pageIndex) => {
      const fields: Record<string, Box> = {};
      for (const [id, box] of Object.entries(layout.fields)) if (box.page === pageIndex) fields[id] = box;
      const rows: Record<number, Box> = {};
      layout.rows.forEach((box, rowIndex) => {
        if (box.page === pageIndex) rows[rowIndex] = box;
      });
      return { imageUrl: page.image, iframeUrl: null, width: page.width, height: page.height, fields, rows };
    });
  }
  if (!previewUrl) return [];
  if (isPdfUpload) return [{ ...blankPage, iframeUrl: previewUrl }];
  const layout = sample?.layout;
  return [
    {
      ...blankPage,
      imageUrl: previewUrl,
      width: layout?.width ?? 0,
      height: layout?.height ?? 0,
      fields: layout?.fields ?? {},
      rows: Object.fromEntries((layout?.rows ?? []).map((box, index) => [index, box])),
    },
  ];
}

/** How far down the whole stack of pages (0 to 1) a value sits, or null if its position is unknown. */
function progressOf(pages: StagePage[], id: string): number | null {
  const heights = pages.map((page) => (page.width > 0 ? page.height / page.width : 0));
  const total = heights.reduce((sum, h) => sum + h, 0);
  if (total === 0) return null;
  let offset = 0;
  for (let index = 0; index < pages.length; index += 1) {
    const box = id.startsWith("row:") ? pages[index].rows[Number(id.slice(4))] : pages[index].fields[id];
    if (box) return (offset + ((box.y + box.h / 2) / pages[index].height) * heights[index]) / total;
    offset += heights[index];
  }
  return null;
}

export default function ScanPage() {
  const [options, setOptions] = useState<DocumentOptions | null>(null);
  const [source, setSource] = useState<Source | null>(null);
  const [phase, setPhase] = useState<ScanPhase>("idle");
  const [looping, setLooping] = useState(false);
  const [result, setResult] = useState<ExtractResponse | null>(null);
  const [revealed, setRevealed] = useState<ReadonlySet<string>>(new Set());
  const [activeId, setActiveId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const runId = useRef(0);
  const fileInput = useRef<HTMLInputElement>(null);
  const autoStart = useRef(false);

  const later = useCallback((ms: number, fn: () => void) => {
    timers.current.push(setTimeout(fn, ms));
  }, []);

  const clearTimers = useCallback(() => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  }, []);

  useEffect(() => clearTimers, [clearTimers]);

  const sampleOf = useCallback(
    (id: string): DocumentSample | undefined => options?.samples.find((s) => s.id === id),
    [options],
  );

  const stop = useCallback(() => {
    runId.current += 1;
    clearTimers();
    setPhase("idle");
    setLooping(false);
    setResult(null);
    setRevealed(new Set());
    setActiveId(null);
    setError(null);
  }, [clearTimers]);

  useEffect(() => {
    getDocumentOptions()
      .then((loaded) => {
        const params = new URLSearchParams(window.location.search);
        const wanted = loaded.samples.find((s) => s.id === params.get("sample")) ?? loaded.samples[0];
        autoStart.current = params.get("autoscan") === "1";
        setOptions(loaded);
        setSource({ kind: "sample", sampleId: wanted.id });
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!source) return;
    if (source.kind === "sample") {
      setPreviewUrl(sampleDocumentUrl(source.sampleId));
      return;
    }
    const url = URL.createObjectURL(source.file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [source]);

  const sample = source?.kind === "sample" ? sampleOf(source.sampleId) : undefined;
  const isPdfUpload = source?.kind === "upload" && source.file.type === "application/pdf";
  const pages = useMemo(
    () => buildPages(result, previewUrl, isPdfUpload, sample),
    [result, previewUrl, isPdfUpload, sample],
  );

  const reveal = (id: string) => setRevealed((prev) => new Set(prev).add(id));

  const scan = useCallback(async () => {
    if (!source) return;
    stop();
    const id = runId.current;
    const started = performance.now();
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    setPhase("scanning");
    later(LOOP_AFTER_MS, () => setLooping(true));

    let data: ExtractResponse;
    try {
      data = await extractDocument({
        verificationType:
          source.kind === "sample" ? (sampleOf(source.sampleId)?.verification_type ?? "") : source.verificationType,
        declared: {},
        sampleId: source.kind === "sample" ? source.sampleId : null,
        live: source.kind === "upload",
        file: source.kind === "upload" ? source.file : null,
        categorize: false,
      });
    } catch (err) {
      if (id !== runId.current) return;
      clearTimers();
      setPhase("idle");
      setLooping(false);
      setError((err as Error).message);
      return;
    }
    if (id !== runId.current) return;

    setLooping(false);
    setResult(data);

    const drawn = buildPages(data, previewUrl, isPdfUpload, sample);
    const elapsed = performance.now() - started;
    let sequence = 0;
    let lastAt = 0;
    const schedule = (revealId: string) => {
      const progress = progressOf(drawn, revealId);
      let at: number;
      if (reduced) at = 0;
      else if (progress !== null) at = progress * SWEEP_MS;
      else at = Math.max(elapsed, SWEEP_MS) + sequence++ * SEQUENTIAL_MS;
      const delay = Math.max(0, at - elapsed);
      lastAt = Math.max(lastAt, delay);
      later(delay, () => reveal(revealId));
    };

    for (const field of data.fields) schedule(field.id);
    (data.transactions ?? []).forEach((_, index) => schedule(`row:${index}`));

    later(Math.max(lastAt, SWEEP_MS - elapsed) + 300, () => setPhase("done"));
  }, [source, sample, isPdfUpload, previewUrl, sampleOf, stop, later, clearTimers]);

  useEffect(() => {
    if (options && source && autoStart.current) {
      autoStart.current = false;
      void scan();
    }
  }, [options, source, scan]);

  const chooseSample = (sampleId: string) => {
    stop();
    setSource({ kind: "sample", sampleId });
  };

  const chooseUpload = (file: File) => {
    stop();
    setSource({
      kind: "upload",
      file,
      verificationType: source?.kind === "upload" ? source.verificationType : DEFAULT_UPLOAD_TYPE,
    });
  };

  const scanning = phase === "scanning";
  const hasBoxes = pages.some((page) => Object.keys(page.fields).length > 0);

  return (
    <div className="min-h-dvh">
      <header className="flex items-center justify-between gap-4 border-b border-border px-6 py-3">
        <div className="flex items-center gap-3">
          <ScanLine className="h-5 w-5 text-primary" aria-hidden="true" />
          <div>
            <h1 className="text-base font-semibold leading-tight">Document Scan</h1>
            <p className="text-xs text-muted-foreground">Watch a document being read and its values pulled out. Nothing is saved.</p>
          </div>
        </div>
        <nav className="flex items-center gap-4 text-xs font-medium text-primary">
          <Link href="/playground/documents" className="underline-offset-4 hover:underline">
            Document Lab
          </Link>
          <Link href="/playground" className="underline-offset-4 hover:underline">
            Assessment Lab
          </Link>
        </nav>
      </header>

      {error && (
        <div role="alert" className="border-b border-destructive/30 bg-destructive/10 px-6 py-2.5 text-sm text-destructive">
          {error}
        </div>
      )}

      {options && source ? (
        <div className="mx-auto max-w-6xl space-y-5 p-6">
          <div className="flex flex-wrap items-center gap-2">
            {options.samples.map((item) => {
              const selected = source.kind === "sample" && source.sampleId === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => chooseSample(item.id)}
                  aria-pressed={selected}
                  disabled={scanning}
                  className={cn(
                    "flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50",
                    selected ? "border-primary bg-primary text-primary-foreground" : "border-border hover:bg-secondary",
                  )}
                >
                  <FileText className="h-4 w-4" aria-hidden="true" />
                  {item.label}
                </button>
              );
            })}
            <button
              type="button"
              onClick={() => fileInput.current?.click()}
              aria-pressed={source.kind === "upload"}
              disabled={scanning}
              className={cn(
                "flex items-center gap-2 rounded-full border border-dashed px-4 py-2 text-sm font-medium transition-colors disabled:opacity-50",
                source.kind === "upload" ? "border-primary bg-primary text-primary-foreground" : "border-border hover:bg-secondary",
              )}
            >
              <Upload className="h-4 w-4" aria-hidden="true" />
              {source.kind === "upload" ? source.file.name : "Upload your own"}
            </button>
            <input
              ref={fileInput}
              type="file"
              accept="image/png,image/jpeg,image/webp,application/pdf"
              className="sr-only"
              aria-label="Upload a document"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file) chooseUpload(file);
                event.target.value = "";
              }}
            />
          </div>

          {source.kind === "upload" && (
            <div className="flex max-w-md items-center gap-3">
              <label htmlFor="upload-type" className="shrink-0 text-xs font-medium text-muted-foreground">
                This should be a
              </label>
              <Select
                id="upload-type"
                value={source.verificationType}
                disabled={scanning}
                onChange={(event) => {
                  stop();
                  setSource({ ...source, verificationType: event.target.value });
                }}
                className="h-9"
              >
                {options.document_types.map((type) => (
                  <option key={type.code} value={type.code}>
                    {type.name}
                  </option>
                ))}
              </Select>
            </div>
          )}

          <div className="grid gap-8 lg:grid-cols-[minmax(320px,560px)_minmax(0,1fr)]">
            <div className="space-y-3">
              <ScanStage
                pages={pages}
                phase={phase}
                looping={looping}
                sweepMs={SWEEP_MS}
                revealed={revealed}
                activeId={activeId}
              />
              <div className="flex items-center gap-3">
                <Button size="lg" onClick={() => void scan()} disabled={scanning}>
                  {scanning ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                      {looping ? "Still reading…" : "Scanning…"}
                    </>
                  ) : (
                    <>
                      <ScanLine className="mr-2 h-4 w-4" aria-hidden="true" />
                      {phase === "done" ? "Scan again" : "Scan document"}
                    </>
                  )}
                </Button>
                {source.kind === "upload" && (
                  <p className="text-xs text-muted-foreground">
                    A digital bank statement PDF is read instantly. Anything else goes to the AI model, which can take 10 to 20 seconds.
                  </p>
                )}
              </div>
              <p className="text-[11px] text-muted-foreground">
                The sweep is a visual guide. The document is read in one go.
                {source.kind === "upload" && " Highlights on the page appear for sample documents and digital bank statement PDFs."}
              </p>
            </div>

            <ValuesPanel
              result={result}
              phase={phase}
              revealed={revealed}
              hasBoxes={hasBoxes}
              sampleId={sample?.id ?? null}
              onActive={setActiveId}
            />
          </div>
        </div>
      ) : (
        !error && <p className="p-6 text-sm text-muted-foreground">Loading…</p>
      )}
    </div>
  );
}
