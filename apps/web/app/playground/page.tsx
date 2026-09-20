"use client";

import { FlaskConical, Loader2 } from "lucide-react";
import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { InputsPanel, type LabState } from "@/components/playground/inputs-panel";
import { ResultsPanel } from "@/components/playground/results-panel";
import { Button } from "@/components/ui/button";
import { getPlaygroundOptions, runPlaygroundAssessment } from "@/lib/api";
import type {
  AssessRequest,
  AssessResponse,
  FilledValue,
  PlaygroundOptions,
  Preset,
} from "@/lib/types/playground";

const DEBOUNCE_MS = 350;

function stateFromPreset(preset: Preset): LabState {
  return {
    presetId: preset.id,
    productCode: preset.product_code,
    filled: { ...preset.filled },
    bureauScenario: preset.bureau_scenario,
    useSampleStatement: preset.use_sample_statement,
    bufferPct: "",
  };
}

function buildRequest(state: LabState): AssessRequest {
  const buffer = Number(state.bufferPct);
  return {
    product_code: state.productCode,
    filled: state.filled,
    bureau_scenario: state.bureauScenario,
    use_sample_statement: state.useSampleStatement,
    policy_overrides:
      state.bufferPct.trim() !== "" && Number.isFinite(buffer)
        ? { assessment_rate_buffer: { buffer_pct: buffer } }
        : undefined,
  };
}

export default function PlaygroundPage() {
  const [options, setOptions] = useState<PlaygroundOptions | null>(null);
  const [state, setState] = useState<LabState | null>(null);
  const [response, setResponse] = useState<AssessResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadOptions = useCallback(() => {
    setError(null);
    getPlaygroundOptions()
      .then((loaded) => {
        const wanted = new URLSearchParams(window.location.search).get("preset");
        setOptions(loaded);
        setState(stateFromPreset(loaded.presets.find((p) => p.id === wanted) ?? loaded.presets[0]));
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(loadOptions, [loadOptions]);

  useEffect(() => {
    if (!state) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      setRunning(true);
      try {
        const result = await runPlaygroundAssessment(buildRequest(state), controller.signal);
        setResponse(result);
        setError(null);
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setError((err as Error).message);
      } finally {
        if (!controller.signal.aborted) setRunning(false);
      }
    }, DEBOUNCE_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [state]);

  const selectPreset = (presetId: string) => {
    const preset = options?.presets.find((p) => p.id === presetId);
    if (!preset) return;
    setState(stateFromPreset(preset));
    window.history.replaceState(null, "", `?preset=${preset.id}`);
  };

  const changeSettings = (patch: Partial<Omit<LabState, "filled">>) =>
    setState((prev) => (prev ? { ...prev, ...patch } : prev));

  const changeField = (key: string, value: FilledValue | undefined) =>
    setState((prev) => {
      if (!prev) return prev;
      const filled = { ...prev.filled };
      if (value === undefined) delete filled[key];
      else filled[key] = value;
      return { ...prev, filled };
    });

  return (
    <div className="flex min-h-dvh flex-col lg:h-dvh">
      <header className="flex items-center justify-between gap-4 border-b border-border px-6 py-3">
        <div className="flex items-center gap-3">
          <FlaskConical className="h-5 w-5 text-primary" aria-hidden="true" />
          <div>
            <h1 className="text-base font-semibold leading-tight">Assessment Lab</h1>
            <p className="text-xs text-muted-foreground">
              Change any input and the real assessment engine re-runs. Nothing is saved.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-4 text-xs">
          <span className="flex items-center gap-2 text-muted-foreground" aria-live="polite">
            {running ? (
              <>
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                Assessing…
              </>
            ) : response ? (
              "Up to date"
            ) : null}
          </span>
          <Link href="/playground/documents" className="font-medium text-primary underline-offset-4 hover:underline">
            Document Lab
          </Link>
          <Link href="/playground/scan" className="font-medium text-primary underline-offset-4 hover:underline">
            Document Scan
          </Link>
        </div>
      </header>

      {error && (
        <div role="alert" className="flex items-center justify-between gap-4 border-b border-destructive/30 bg-destructive/10 px-6 py-2.5 text-sm text-destructive">
          <span>{error}</span>
          {!options && (
            <Button variant="outline" size="sm" onClick={loadOptions}>
              Retry
            </Button>
          )}
        </div>
      )}

      {options && state ? (
        <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
          <aside className="w-full shrink-0 border-b border-border lg:w-[440px] lg:overflow-y-auto lg:border-b-0 lg:border-r">
            <InputsPanel
              options={options}
              state={state}
              onPreset={selectPreset}
              onChange={changeSettings}
              onField={changeField}
            />
          </aside>
          <main className="min-w-0 flex-1 lg:overflow-y-auto">
            {response ? (
              <ResultsPanel response={response} />
            ) : (
              <p className="p-6 text-sm text-muted-foreground">Running the first assessment…</p>
            )}
          </main>
        </div>
      ) : (
        !error && <p className="p-6 text-sm text-muted-foreground">Loading…</p>
      )}
    </div>
  );
}
