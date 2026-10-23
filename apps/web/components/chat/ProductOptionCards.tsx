import type { ProductOption } from "@/lib/agent-api";



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
    <div className="mt-3 grid max-w-2xl gap-3 sm:grid-cols-2">
      {products.map((p) => (
        <div
          key={p.product_code}
          className="flex flex-col rounded-lg border border-slate-200 bg-white p-4 transition-colors hover:border-[#0F6E56]/60"
        >
          <p className="font-semibold text-slate-900">{p.name}</p>
          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            <span className="inline-flex items-center rounded-full bg-[#e6f2ee] px-2.5 py-0.5 text-xs font-semibold text-[#0F6E56]">
              {rateLabel(p)}
            </span>
          </div>
          <dl className="mt-3 space-y-1 text-sm text-slate-500">
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
            className="mt-4 rounded-md bg-[#0F6E56] px-3 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-[#0c5a46] disabled:cursor-not-allowed disabled:opacity-40 disabled:hover:bg-[#0F6E56]"
          >
            Select
          </button>
        </div>
      ))}
    </div>
  );
}
