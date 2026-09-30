"use client";

import { FileText, Loader2, Upload } from "lucide-react";
import { useRef } from "react";

import { Button } from "@/components/kit/button";
import { Input } from "@/components/kit/input";
import { Select } from "@/components/kit/select";
import { describeCheck } from "@/lib/documents/labels";
import type { DocumentOptions } from "@/lib/types/documents";
import { cn } from "@/lib/utils";

export type LabSource = { kind: "sample"; sampleId: string } | { kind: "upload"; file: File };

export type DocLabState = {
  source: LabSource;
  verificationType: string;
  declared: Record<string, string>;
  live: boolean;
};

type Props = {
  options: DocumentOptions;
  state: DocLabState;
  running: boolean;
  onSample: (sampleId: string) => void;
  onUpload: (file: File) => void;
  onType: (verificationType: string) => void;
  onDeclared: (slotId: string, value: string) => void;
  onMismatch: () => void;
  onRestoreDeclared: () => void;
  onLive: (live: boolean) => void;
  onExtract: () => void;
};

const ACCEPT = "image/png,image/jpeg,image/webp,application/pdf";

export function SourcePanel(props: Props) {
  const { options, state, running } = props;
  const fileInput = useRef<HTMLInputElement>(null);

  const source = state.source;
  const sample = source.kind === "sample" ? options.samples.find((s) => s.id === source.sampleId) : undefined;
  const docType = options.document_types.find((t) => t.code === state.verificationType);
  const isUpload = state.source.kind === "upload";
  const auto = !isUpload && !state.live;

  return (
    <div className="space-y-6 p-5">
      <section className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">1. Choose a document</h2>
        <div className="space-y-2">
          {options.samples.map((item) => {
            const selected = state.source.kind === "sample" && state.source.sampleId === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => props.onSample(item.id)}
                aria-pressed={selected}
                className={cn(
                  "flex w-full items-start gap-3 rounded-lg border p-3 text-left transition-colors",
                  selected ? "border-primary bg-primary/5" : "border-border hover:bg-secondary/50",
                )}
              >
                <FileText className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                <span>
                  <span className="block text-sm font-medium">{item.label}</span>
                  <span className="block text-xs text-muted-foreground">{item.description}</span>
                </span>
              </button>
            );
          })}
          <button
            type="button"
            onClick={() => fileInput.current?.click()}
            aria-pressed={isUpload}
            className={cn(
              "flex w-full items-start gap-3 rounded-lg border border-dashed p-3 text-left transition-colors",
              isUpload ? "border-primary bg-primary/5" : "border-border hover:bg-secondary/50",
            )}
          >
            <Upload className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
            <span>
              <span className="block text-sm font-medium">
                {state.source.kind === "upload" ? state.source.file.name : "Upload your own"}
              </span>
              <span className="block text-xs text-muted-foreground">
                PNG, JPEG, WebP or PDF up to 10 MB. Always read live by the AI model.
              </span>
            </span>
          </button>
          <input
            ref={fileInput}
            type="file"
            accept={ACCEPT}
            className="sr-only"
            aria-label="Upload a document"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) props.onUpload(file);
              event.target.value = "";
            }}
          />
        </div>
      </section>

      <section className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          2. What kind of document is it meant to be?
        </h2>
        <Select
          value={state.verificationType}
          onChange={(event) => props.onType(event.target.value)}
          disabled={auto}
          aria-label="Document type"
        >
          {options.document_types.map((type) => (
            <option key={type.code} value={type.code}>
              {type.name}
            </option>
          ))}
        </Select>
        <p className="text-xs text-muted-foreground">
          {auto
            ? "Locked to the sample's own type while replaying the recorded run. Turn on live reading to try another type, for example a payslip submitted as a photo ID."
            : "The applicant is asked for a specific document. The AI first checks that this is really it."}
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          3. What did the applicant say?
        </h2>
        {docType && docType.checks.length > 0 ? (
          <>
            {docType.checks.map((check) => (
              <div key={check.slot_id}>
                <label htmlFor={`declared-${check.slot_id}`} className="mb-1 block text-xs font-medium text-muted-foreground">
                  {check.label}
                </label>
                <Input
                  id={`declared-${check.slot_id}`}
                  value={state.declared[check.slot_id] ?? ""}
                  placeholder="Not provided"
                  onChange={(event) => props.onDeclared(check.slot_id, event.target.value)}
                  className="h-9"
                />
                <p className="mt-1 text-[11px] text-muted-foreground">{describeCheck(check.compare, check.tolerance_pct)}</p>
              </div>
            ))}
            {sample && (
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={props.onMismatch}>
                  Try a mismatch
                </Button>
                <Button variant="ghost" size="sm" onClick={props.onRestoreDeclared}>
                  Restore
                </Button>
              </div>
            )}
          </>
        ) : (
          <p className="text-xs text-muted-foreground">
            No interview answers are compared for this document type. Its fields are simply kept on file.
          </p>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">4. Read it</h2>
        <label className={cn("flex items-start justify-between gap-3", isUpload && "opacity-70")}>
          <span>
            <span className="block text-sm font-medium">Run the AI model live</span>
            <span className="block text-xs text-muted-foreground">
              {isUpload
                ? "Uploads always run live."
                : "Off replays a real run saved earlier, instantly. On calls the model now, which takes 10 to 20 seconds and uses request quota."}
            </span>
          </span>
          <input
            type="checkbox"
            role="switch"
            checked={isUpload || state.live}
            disabled={isUpload}
            onChange={(event) => props.onLive(event.target.checked)}
            className="mt-1 h-4 w-4 accent-[hsl(var(--primary))]"
          />
        </label>

        {auto ? (
          <p className="text-xs text-muted-foreground">Results update as you change the declared answers.</p>
        ) : (
          <Button className="w-full" size="lg" onClick={props.onExtract} disabled={running}>
            {running ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" aria-hidden="true" />
                Reading document…
              </>
            ) : (
              "Extract"
            )}
          </Button>
        )}
      </section>
    </div>
  );
}
