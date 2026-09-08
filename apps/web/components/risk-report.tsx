import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type {
  DataSourceEntry,
  FiveCField,
  FiveCKey,
  MissingField,
  RiskAssessmentReport,
} from "@/lib/types/risk-assessment";

const FIVE_C_ORDER: FiveCKey[] = ["character", "capacity", "capital", "collateral", "conditions"];

const FIVE_C_LABELS: Record<FiveCKey, string> = {
  character: "Character",
  capacity: "Capacity",
  capital: "Capital",
  collateral: "Collateral",
  conditions: "Conditions",
};

const SOURCE_LABELS: Record<FiveCField["source"], string> = {
  "bureau-verified": "Bureau-verified",
  "abn-verified": "ABN-verified",
  "applicant-declared": "Applicant-declared",
  calculated: "Calculated",
  unavailable: "Unavailable",
};

function prettifyKey(key: string): string {
  const spaced = key.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number")
    return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  return String(value);
}

function confidenceBadgeVariant(
  confidence: FiveCField["confidence"],
): "success" | "warning" | "muted" {
  if (confidence === "high") return "success";
  if (confidence === "medium") return "warning";
  return "muted";
}

interface RequestDetailsControl {
  onRequestDetails: (fiveC: FiveCKey) => void;
  requestingC: FiveCKey | null;
  requestedCs: Set<FiveCKey>;
}

function RequestDetailsButton({
  fiveC,
  control,
}: {
  fiveC: FiveCKey;
  control: RequestDetailsControl;
}) {
  const isRequesting = control.requestingC === fiveC;
  const wasRequested = control.requestedCs.has(fiveC);

  return (
    <div className="mt-3 border-t border-border pt-3">
      <Button
        type="button"
        variant={wasRequested ? "outline" : "default"}
        size="sm"
        onClick={() => control.onRequestDetails(fiveC)}
        disabled={isRequesting || wasRequested}
      >
        {wasRequested
          ? "Details requested"
          : isRequesting
            ? "Sending request..."
            : "Request further details"}
      </Button>
    </div>
  );
}

function FiveCCard({
  fiveC,
  label,
  field,
  requestDetails,
}: {
  fiveC: FiveCKey;
  label: string;
  field: FiveCField;
  requestDetails?: RequestDetailsControl;
}) {
  const isUnavailable = field.source === "unavailable" || field.value == null;
  const valueEntries =
    field.value && typeof field.value === "object" && !Array.isArray(field.value)
      ? Object.entries(field.value as Record<string, unknown>)
      : null;

  return (
    <div className="rounded-lg border border-border p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">{label}</h3>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant="outline" className="text-xs">
            {SOURCE_LABELS[field.source]}
          </Badge>
          <Badge variant={confidenceBadgeVariant(field.confidence)} className="text-xs capitalize">
            {field.confidence} confidence
          </Badge>
        </div>
      </div>

      {isUnavailable ? (
        <p className="text-sm italic text-muted-foreground">
          Unavailable — not enough data to assess this yet.
        </p>
      ) : valueEntries ? (
        <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
          {valueEntries.map(([key, value]) => (
            <div
              key={key}
              className="flex items-baseline justify-between gap-3 sm:flex-col sm:items-start sm:gap-0.5"
            >
              <dt className="text-muted-foreground">{prettifyKey(key)}</dt>
              <dd className="font-medium">{formatValue(value)}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="text-sm font-medium">{formatValue(field.value)}</p>
      )}

      {field.notes && <p className="mt-3 text-xs text-muted-foreground">{field.notes}</p>}

      {requestDetails && <RequestDetailsButton fiveC={fiveC} control={requestDetails} />}
    </div>
  );
}

function MissingFieldsPanel({ missingFields }: { missingFields: MissingField[] }) {
  const grouped = FIVE_C_ORDER.map((key) => ({
    key,
    label: FIVE_C_LABELS[key],
    fields: missingFields.filter((f) => f.five_c === key),
  })).filter((group) => group.fields.length > 0);

  return (
    <div className="rounded-lg border border-border p-4">
      <h3 className="mb-3 font-semibold">Missing data</h3>
      {grouped.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          No gaps — every checklist field for this application was present.
        </p>
      ) : (
        <div className="space-y-4">
          {grouped.map((group) => (
            <div key={group.key}>
              <p className="mb-1.5 text-sm font-medium">{group.label}</p>
              <ul className="space-y-1.5">
                {group.fields.map((field) => (
                  <li
                    key={field.field}
                    className="flex flex-wrap items-center justify-between gap-2 text-sm"
                  >
                    <span className="text-muted-foreground">{field.label}</span>
                    <Badge
                      variant={field.requirement === "required" ? "warning" : "muted"}
                      className="text-xs"
                    >
                      {field.requirement === "required" ? "Required" : "Improves confidence"}
                    </Badge>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DataSourceBadge({ entry }: { entry: DataSourceEntry }) {
  if (!entry.called) {
    return (
      <Badge variant="muted" className="text-xs">
        Not called{entry.reason ? ` — ${entry.reason}` : ""}
      </Badge>
    );
  }
  if (entry.matched === true) {
    return (
      <Badge variant="success" className="text-xs">
        Matched
      </Badge>
    );
  }
  if (entry.matched === false) {
    return (
      <Badge variant="muted" className="text-xs">
        No match
      </Badge>
    );
  }
  return (
    <Badge variant="warning" className="text-xs">
      Unavailable{entry.reason ? ` — ${entry.reason}` : ""}
    </Badge>
  );
}

function DataSourcesPanel({ dataSources }: { dataSources: DataSourceEntry[] }) {
  return (
    <div className="rounded-lg border border-border p-4">
      <h3 className="mb-3 font-semibold">Data sources</h3>
      <ul className="space-y-2.5">
        {dataSources.map((entry) => (
          <li
            key={entry.source}
            className="flex flex-wrap items-center justify-between gap-2 text-sm"
          >
            <span className="capitalize">{entry.source.replace(/_/g, " ")}</span>
            <DataSourceBadge entry={entry} />
          </li>
        ))}
      </ul>
    </div>
  );
}

export function RiskReportView({
  report,
  requestDetails,
}: {
  report: RiskAssessmentReport;
  /** Omit entirely (e.g. on the standalone /risk-assessment sandbox page, which has no real
   * conversation to attach a request to) to hide the "Request further details" button. */
  requestDetails?: RequestDetailsControl;
}) {
  return (
    <div className="flex flex-col gap-4">
      <div className="rounded-lg border border-border p-4">
        <div className="flex items-center justify-between gap-2">
          <span className="font-semibold">Completeness</span>
          <Badge variant="outline">{Math.round(report.completeness.score * 100)}%</Badge>
        </div>
        <p className="mt-1 text-xs text-muted-foreground">
          Application {report.application_id} · assessed{" "}
          {new Date(report.assessed_at).toLocaleString()}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {FIVE_C_ORDER.map((key) => (
          <FiveCCard
            key={key}
            fiveC={key}
            label={FIVE_C_LABELS[key]}
            field={report.five_cs[key]}
            requestDetails={requestDetails}
          />
        ))}
      </div>

      <MissingFieldsPanel missingFields={report.completeness.missing_fields} />
      <DataSourcesPanel dataSources={report.data_sources} />
    </div>
  );
}
