"use client";

import { FileSearch, Loader2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { ResultSteps } from "@/components/documents/result-steps";
import { SourcePanel, type DocLabState } from "@/components/documents/source-panel";
import { Button } from "@/components/kit/button";
import { ExtractionError, extractDocument, getDocumentOptions, sampleDocumentUrl } from "@/lib/playground-api";
import type { DocumentOptions, DocumentSample, ExtractResponse } from "@/lib/types/documents";

const AUTO_DEBOUNCE_MS = 300;
const DEFAULT_UPLOAD_TYPE = "payslip_or_contract";

type LabError = { message: string; status?: number };

function sampleState(sample: DocumentSample, mismatch = false): DocLabState {
  return {
    source: { kind: "sample", sampleId: sample.id },
    verificationType: sample.verification_type,
    declared: { ...(mismatch ? sample.mismatch_example : sample.declared) },
    live: false,
  };
}

const isAuto = (state: DocLabState) => state.source.kind === "sample" && !state.live;

export default function DocumentLabPage() {
  const [options, setOptions] = useState<DocumentOptions | null>(null);
  const [state, setState] = useState<DocLabState | null>(null);
  const [response, setResponse] = useState<ExtractResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [stale, setStale] = useState(false);
  const [error, setError] = useState<LabError | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const controller = useRef<AbortController | null>(null);

  const loadOptions = useCallback(() => {
    setError(null);
    getDocumentOptions()
      .then((loaded) => {
        const params = new URLSearchParams(window.location.search);
        const wanted = loaded.samples.find((s) => s.id === params.get("sample")) ?? loaded.samples[0];
        setOptions(loaded);
        setState(sampleState(wanted, params.get("mismatch") === "1"));
      })
      .catch((err: Error) => setError({ message: err.message }));
  }, []);

  useEffect(loadOptions, [loadOptions]);

  useEffect(() => {
    if (!state) return;
    if (state.source.kind === "sample") {
      setPreviewUrl(sampleDocumentUrl(state.source.sampleId));
      return;
    }
    const url = URL.createObjectURL(state.source.file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [state?.source]); 

  const run = useCallback(async (current: DocLabState) => {
    controller.current?.abort();
    const abort = new AbortController();
    controller.current = abort;
    setRunning(true);
    try {
      const result = await extractDocument(
        {
          verificationType: current.verificationType,
          declared: current.declared,
          sampleId: current.source.kind === "sample" ? current.source.sampleId : null,
          live: current.source.kind === "upload" || current.live,
          file: current.source.kind === "upload" ? current.source.file : null,
        },
        abort.signal,
      );
      setResponse(result);
      setError(null);
      setStale(false);
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setError({ message: (err as Error).message, status: err instanceof ExtractionError ? err.status : undefined });
    } finally {
      if (!abort.signal.aborted) setRunning(false);
    }
  }, []);

  useEffect(() => {
    if (!state || !isAuto(state)) return;
    const timer = setTimeout(() => void run(state), AUTO_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [state, run]);

  const sampleOf = (id: string) => options?.samples.find((s) => s.id === id);

  const reset = (next: DocLabState) => {
    controller.current?.abort();
    setRunning(false);
    setResponse(null);
    setError(null);
    setStale(false);
    setState(next);
  };

  const chooseSample = (id: string) => {
    const sample = sampleOf(id);
    if (sample) reset(sampleState(sample));
  };

  const chooseUpload = (file: File) =>
    reset({
      source: { kind: "upload", file },
      verificationType: state?.source.kind === "upload" ? state.verificationType : DEFAULT_UPLOAD_TYPE,
      declared: {},
      live: true,
    });

  const chooseType = (verificationType: string) => {
    if (!state) return;
    const sample = state.source.kind === "sample" ? sampleOf(state.source.sampleId) : undefined;
    const declared = sample && sample.verification_type === verificationType ? { ...sample.declared } : {};
    setResponse(null);
    setStale(false);
    setState({ ...state, verificationType, declared });
  };

  const changeDeclared = (slotId: string, value: string) => {
    if (!state) return;
    if (!isAuto(state)) setStale(true);
    setState({ ...state, declared: { ...state.declared, [slotId]: value } });
  };

  const setDeclared = (values: Record<string, string> | undefined) => {
    if (!state || !values) return;
    if (!isAuto(state)) setStale(true);
    setState({ ...state, declared: { ...values } });
  };

  const changeLive = (live: boolean) => {
    if (!state) return;
    const sample = state.source.kind === "sample" ? sampleOf(state.source.sampleId) : undefined;
    if (!live && sample) {
      reset(sampleState(sample));
      return;
    }
    setResponse(null);
    setStale(false);
    setState({ ...state, live });
  };

  const currentSample = state?.source.kind === "sample" ? sampleOf(state.source.sampleId) : undefined;
  const docType = options?.document_types.find((t) => t.code === state?.verificationType);
  const isPdf = state?.source.kind === "upload" && state.source.file.type === "application/pdf";
  const manualRunning = running && state !== null && !isAuto(state);

  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh">
      <header className="flex items-center justify-between gap-4 border-b border-border px-6 py-3">
        <div className="flex items-center gap-3">
          <FileSearch className="h-5 w-5 text-primary" aria-hidden="true" />
          <div>
            <h1 className="text-base font-semibold leading-tight">Document Lab</h1>
            <p className="text-xs text-muted-foreground">
              See how an uploaded document is read, checked against what the applicant said, and used in the assessment.
              Nothing is saved.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-2 text-muted-foreground" aria-live="polite">
            {running ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                Working…
              </>
            ) : response ? (
              "Up to date"
            ) : null}
          </span>
          <Link href="/playground/scan" className="font-medium text-primary underline-offset-4 hover:underline">
            Document Scan
          </Link>
          <Link href="/playground" className="font-medium text-primary underline-offset-4 hover:underline">
            Assessment Lab
          </Link>
        </div>
      </header>

      {error && (
        <div
          role="alert"
          className="flex items-center justify-between gap-4 border-b border-destructive/30 bg-destructive/10 px-6 py-2.5 text-sm text-destructive"
        >
          <span>{error.message}</span>
          {!options && (
            <Button variant="outline" size="sm" onClick={loadOptions}>
              Retry
            </Button>
          )}
          {options && error.status === 429 && currentSample?.recording && (
            <Button variant="outline" size="sm" onClick={() => changeLive(false)}>
              Show the recorded result
            </Button>
          )}
        </div>
      )}

      {options && state ? (
        <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
          <aside className="w-full shrink-0 border-b border-border lg:w-[440px] lg:overflow-y-auto lg:border-b-0 lg:border-r">
            <SourcePanel
              options={options}
              state={state}
              running={running}
              onSample={chooseSample}
              onUpload={chooseUpload}
              onType={chooseType}
              onDeclared={changeDeclared}
              onMismatch={() => setDeclared(currentSample?.mismatch_example)}
              onRestoreDeclared={() => setDeclared(currentSample?.declared)}
              onLive={changeLive}
              onExtract={() => void run(state)}
            />
          </aside>

          <main className="min-w-0 flex-1 lg:overflow-y-auto">
            <div className="grid gap-6 p-6 xl:grid-cols-[minmax(300px,420px)_minmax(0,1fr)]">
              <section className="self-start xl:sticky xl:top-0">
                <h2 className="mb-2 text-sm font-semibold">The document</h2>
                <div className="overflow-hidden rounded-xl border border-border bg-secondary/30">
                  {previewUrl &&
                    (isPdf ? (
                      <iframe src={previewUrl} title="Uploaded document" className="h-[560px] w-full" />
                    ) : (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={previewUrl} alt="The selected document" className="w-full" />
                    ))}
                </div>
              </section>

              <section className="min-w-0">
                <h2 className="mb-2 text-sm font-semibold">What happens to it</h2>
                {stale && (
                  <p className="mb-3 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
                    The inputs have changed since this result. Press Extract to refresh it.
                  </p>
                )}
                {manualRunning ? (
                  <div className="flex items-center gap-3 rounded-xl border border-border p-6 text-sm text-muted-foreground">
                    <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" />
                    The AI model is reading the document. This usually takes 10 to 20 seconds.
                  </div>
                ) : response ? (
                  <ResultSteps response={response} docType={docType} />
                ) : (
                  !error && (
                    <p className="rounded-xl border border-dashed border-border p-6 text-sm text-muted-foreground">
                      {isAuto(state) ? "Loading the recorded result…" : "Press Extract to read the document."}
                    </p>
                  )
                )}
              </section>
            </div>
          </main>
        </div>
      ) : (
        !error && <p className="p-6 text-sm text-muted-foreground">Loading…</p>
      )}
    </div>
  );
}
