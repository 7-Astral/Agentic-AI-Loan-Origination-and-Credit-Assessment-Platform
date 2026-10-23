"use client";

import { ChevronRight, RotateCcw } from "lucide-react";

import { Button } from "@/components/kit/button";
import { Input } from "@/components/kit/input";
import { Select } from "@/components/kit/select";
import { SECTIONS, prettify, type Field } from "@/lib/playground/fields";
import type { Filled, FilledValue, PlaygroundOptions, PlaygroundProduct } from "@/lib/types/playground";
import { cn } from "@/lib/utils";

export type LabState = {
  presetId: string;
  productCode: string;
  filled: Filled;
  bureauScenario: string;
  useSampleStatement: boolean;
  bufferPct: string;
};

type Props = {
  options: PlaygroundOptions;
  state: LabState;
  onPreset: (presetId: string) => void;
  onChange: (patch: Partial<Omit<LabState, "filled">>) => void;
  onField: (key: string, value: FilledValue | undefined) => void;
};

const OPEN_BY_DEFAULT = new Set(["loan", "income", "home_deposit", "vehicle_deposit"]);

const money = (n: number) =>
  new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD", maximumFractionDigits: 0 }).format(n);

function limitHint(field: Field, product: PlaygroundProduct | undefined, value: FilledValue | undefined) {
  if (!product || typeof value !== "number") return null;
  if (field.key === "loan_amount") {
    const outside = value < product.min_amount || value > product.max_amount;
    return {
      text: `Product allows ${money(product.min_amount)} to ${money(product.max_amount)}`,
      warn: outside,
    };
  }
  if (field.key === "loan_term_months") {
    const outside = value < product.min_term_months || value > product.max_term_months;
    return {
      text: `Product allows ${product.min_term_months} to ${product.max_term_months} months`,
      warn: outside,
    };
  }
  return null;
}

function FieldControl({
  field,
  value,
  onField,
}: {
  field: Field;
  value: FilledValue | undefined;
  onField: Props["onField"];
}) {
  const id = `field-${field.key}`;

  if (field.kind === "toggle") {
    const checked = value === true;
    return (
      <label htmlFor={id} className="flex cursor-pointer items-center justify-between gap-3 py-1">
        <span>
          <span className="block text-sm font-medium">{field.label}</span>
          {field.hint && <span className="block text-xs text-muted-foreground">{field.hint}</span>}
        </span>
        <input
          id={id}
          type="checkbox"
          role="switch"
          checked={checked}
          onChange={(event) => onField(field.key, event.target.checked)}
          className="h-4 w-4 accent-[hsl(var(--primary))]"
        />
      </label>
    );
  }

  if (field.kind === "select") {
    return (
      <div>
        <label htmlFor={id} className="mb-1 block text-xs font-medium text-muted-foreground">
          {field.label}
        </label>
        <Select
          id={id}
          value={typeof value === "string" ? value : ""}
          onChange={(event) => onField(field.key, event.target.value || undefined)}
          className="h-9"
        >
          <option value="">Not provided</option>
          {field.options?.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </Select>
      </div>
    );
  }

  const isNumeric = field.kind === "currency" || field.kind === "number";
  return (
    <div>
      <label htmlFor={id} className="mb-1 block text-xs font-medium text-muted-foreground">
        {field.label}
      </label>
      <div className="relative">
        {field.kind === "currency" && (
          <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-sm text-muted-foreground">
            $
          </span>
        )}
        <Input
          id={id}
          type={isNumeric ? "number" : field.kind}
          inputMode={isNumeric ? "decimal" : undefined}
          min={isNumeric ? 0 : undefined}
          value={typeof value === "boolean" ? "" : (value ?? "")}
          placeholder="Not provided"
          onChange={(event) => {
            const raw = event.target.value;
            if (raw === "") onField(field.key, undefined);
            else onField(field.key, isNumeric ? Number(raw) : raw);
          }}
          className={cn("h-9", field.kind === "currency" && "pl-6")}
        />
      </div>
    </div>
  );
}

export function InputsPanel({ options, state, onPreset, onChange, onField }: Props) {
  const preset = options.presets.find((p) => p.id === state.presetId);
  const product = options.products.find((p) => p.product_code === state.productCode);

  return (
    <div className="space-y-5 p-5">
      <section className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Start from a demo applicant
        </h2>
        <div className="flex gap-2">
          <Select value={state.presetId} onChange={(event) => onPreset(event.target.value)}>
            {options.presets.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </Select>
          <Button
            variant="outline"
            size="lg"
            className="px-3"
            onClick={() => onPreset(state.presetId)}
            title="Reset every field to this applicant"
            aria-label="Reset to preset"
          >
            <RotateCcw className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>
        {preset && <p className="text-xs text-muted-foreground">{preset.description}</p>}
      </section>

      <section className="space-y-2">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Product</h2>
        <Select value={state.productCode} onChange={(event) => onChange({ productCode: event.target.value })}>
          {options.products.map((p) => (
            <option key={p.product_code} value={p.product_code}>
              {p.name} ({p.product_code})
            </option>
          ))}
        </Select>
        {product && (
          <p className="text-xs text-muted-foreground">
            {product.interest_rate}% p.a. · {product.secured ? "Secured" : "Unsecured"}
            {product.max_lvr ? ` · Max LVR ${product.max_lvr}%` : ""}
          </p>
        )}
      </section>

      {SECTIONS.filter((section) => !section.appliesTo || section.appliesTo(product)).map((section) => (
        <details key={section.id} open={OPEN_BY_DEFAULT.has(section.id)} className="group rounded-lg border border-border">
          <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2.5 text-sm font-semibold">
            <ChevronRight
              className="h-4 w-4 text-muted-foreground transition-transform group-open:rotate-90"
              aria-hidden="true"
            />
            {section.title}
          </summary>
          <div className="grid grid-cols-2 gap-x-3 gap-y-3 border-t border-border p-3">
            {section.fields.map((field) => {
              const hint = limitHint(field, product, state.filled[field.key]);
              return (
                <div key={field.key} className={cn((field.kind === "toggle" || field.kind === "text") && "col-span-2")}>
                  <FieldControl field={field} value={state.filled[field.key]} onField={onField} />
                  {hint && (
                    <p className={cn("mt-1 text-[11px]", hint.warn ? "font-medium text-amber-600" : "text-muted-foreground")}>
                      {hint.warn ? "Outside limits. " : ""}
                      {hint.text}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </details>
      ))}

      <details open className="group rounded-lg border border-border">
        <summary className="flex cursor-pointer list-none items-center gap-2 px-3 py-2.5 text-sm font-semibold">
          <ChevronRight
            className="h-4 w-4 text-muted-foreground transition-transform group-open:rotate-90"
            aria-hidden="true"
          />
          Evidence and what-ifs
        </summary>
        <div className="space-y-3 border-t border-border p-3">
          <div>
            <label htmlFor="bureau-scenario" className="mb-1 block text-xs font-medium text-muted-foreground">
              Credit file returned by the bureau
            </label>
            <Select
              id="bureau-scenario"
              value={state.bureauScenario}
              onChange={(event) => onChange({ bureauScenario: event.target.value })}
              className="h-9"
            >
              {options.bureau_scenarios.map((s) => (
                <option key={s.name} value={s.name}>
                  {prettify(s.name)}
                </option>
              ))}
            </Select>
            <p className="mt-1 text-[11px] text-muted-foreground">
              {state.filled.credit_check_consent === true
                ? options.bureau_scenarios.find((s) => s.name === state.bureauScenario)?.description
                : "Not used: the applicant has not consented to a credit check (see Applicant)."}
            </p>
          </div>

          <label className="flex cursor-pointer items-center justify-between gap-3">
            <span>
              <span className="block text-sm font-medium">Applicant uploaded a bank statement</span>
              <span className="block text-xs text-muted-foreground">Three pay credits plus rent, food and insurance</span>
            </span>
            <input
              type="checkbox"
              role="switch"
              checked={state.useSampleStatement}
              onChange={(event) => onChange({ useSampleStatement: event.target.checked })}
              className="h-4 w-4 accent-[hsl(var(--primary))]"
            />
          </label>

          <div>
            <label htmlFor="buffer-pct" className="mb-1 block text-xs font-medium text-muted-foreground">
              Bank policy: assessment rate buffer (percentage points)
            </label>
            <Input
              id="buffer-pct"
              type="number"
              step="0.25"
              min={0}
              value={state.bufferPct}
              placeholder="Bank default"
              onChange={(event) => onChange({ bufferPct: event.target.value })}
              className="h-9"
            />
            <p className="mt-1 text-[11px] text-muted-foreground">
              Repayments are tested at the product rate plus this buffer.
            </p>
          </div>
        </div>
      </details>
    </div>
  );
}
