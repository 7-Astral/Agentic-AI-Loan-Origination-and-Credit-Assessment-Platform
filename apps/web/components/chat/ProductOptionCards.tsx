import type { ProductOption } from "@/lib/agent-api";
import { Badge } from "@/components/ui/Badge";

/**
 * Renders the loan products the assistant is presenting (discovery's
 * product_selection turn) as cards instead of a bulleted wall of text.
 * `interactive` gates whether the Select buttons actually work — only the
 * most recent agent turn should be clickable; once the conversation has
 * moved on, older product cards stay visible as a record of what was
 * offered but no longer do anything if clicked.
 */

function fmtAmount(x: number) {
  return `$${Math.round(x).toLocaleString()}`;
}

function rateLabel(p: ProductOption) {
  if (p.interest_rate == null) return "Rate on request";
  const type = (p.rate_type || "variable").replace(/_/g, " ");
  return `${p.interest_rate}% ${type}`;
}

export function ProductOptionCards({
  products,
  interactive,
  onSelect,
}: {
  products: ProductOption[];
  interactive: boolean;
  onSelect: (product: ProductOption) => void;
}) {
  return (
    <div className="mt-2 grid max-w-2xl gap-2.5 sm:grid-cols-2">
      {products.map((p) => (
        <div
          key={p.product_code}
          className="flex flex-col rounded-xl border border-slate-200 bg-white p-3.5 shadow-sm shadow-slate-200/40"
        >
          <p className="text-sm font-semibold text-slate-900">{p.name}</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            <Badge tone="indigo">{rateLabel(p)}</Badge>
          </div>
          <dl className="mt-2.5 space-y-1 text-xs text-slate-500">
            <div className="flex justify-between gap-2">
              <dt>Amount</dt>
              <dd className="font-medium text-slate-700">
                {fmtAmount(p.min_amount)} – {fmtAmount(p.max_amount)}
              </dd>
            </div>
            <div className="flex justify-between gap-2">
              <dt>Term</dt>
              <dd className="font-medium text-slate-700">
                {p.min_term_months}–{p.max_term_months} months
              </dd>
            </div>
          </dl>
          {p.features.length > 0 && (
            <div className="mt-2.5 flex flex-wrap gap-1">
              {p.features.map((f) => (
                <span
                  key={f}
                  className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium text-slate-500"
                >
                  {f}
                </span>
              ))}
            </div>
          )}
          <button
            type="button"
            disabled={!interactive}
            onClick={() => onSelect(p)}
            className="mt-3 rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 transition-colors hover:border-indigo-300 hover:bg-indigo-100 disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-indigo-50"
          >
            Select
          </button>
        </div>
      ))}
    </div>
  );
}
