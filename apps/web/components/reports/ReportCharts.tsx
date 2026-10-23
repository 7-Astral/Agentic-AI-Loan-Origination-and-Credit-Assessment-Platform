import type { AssessmentReport, FiveC } from "@/lib/api";
import { fmtMoney, humanize } from "./format";

type Step = { label: string; value: number; kind: "total" | "minus" | "plus" | "result" };


const BRAND = "#1f5fa8";
const GRID = "#d6d9de";
const TEXT = "#343a42";
const MUTED = "#8a909a";

const FIVE_C_ORDER: FiveC[] = ["capacity", "capital", "character", "collateral", "conditions"];

export function FiveCRadar({ assessment }: { assessment: AssessmentReport }) {
  const size = 280;
  const c = size / 2;
  const radius = 92;
  const points = FIVE_C_ORDER.map((key, i) => {
    const group = assessment.group_scores[key];
    const score = group && group.state === "computed" && group.score !== null ? group.score : null;
    const angle = -Math.PI / 2 + (i * 2 * Math.PI) / FIVE_C_ORDER.length;
    return { key, score, angle };
  });
  const at = (angle: number, r: number) => [c + Math.cos(angle) * r, c + Math.sin(angle) * r] as const;
  const ring = (value: number) => points.map((p) => at(p.angle, (radius * value) / 100).join(",")).join(" ");
  const shape = points.map((p) => at(p.angle, (radius * (p.score ?? 0)) / 100).join(",")).join(" ");

  const scored = points.filter((p) => p.score !== null);
  const weakest = scored.length ? scored.reduce((a, b) => (a.score! <= b.score! ? a : b)) : null;
  const strongest = scored.length ? scored.reduce((a, b) => (a.score! >= b.score! ? a : b)) : null;

  return (
    <figure className="flex flex-col items-center">
      <svg viewBox={`0 0 ${size} ${size}`} className="h-auto w-full max-w-[300px]" role="img" aria-label="Five C's scores radar chart">
        {[20, 40, 60, 80, 100].map((v) => (
          <polygon
            key={v}
            points={ring(v)}
            fill="none"
            stroke={GRID}
            strokeWidth={v === 60 || v === 80 ? 1.2 : 0.8}
            strokeDasharray={v === 60 || v === 80 ? "4 3" : undefined}
          />
        ))}
        {points.map((p) => {
          const [x, y] = at(p.angle, radius);
          return <line key={p.key} x1={c} y1={c} x2={x} y2={y} stroke={GRID} strokeWidth={0.8} />;
        })}
        <polygon points={shape} fill={BRAND} fillOpacity={0.18} stroke={BRAND} strokeWidth={2} strokeLinejoin="round" />
        {points.map((p) => {
          const [x, y] = at(p.angle, (radius * (p.score ?? 0)) / 100);
          return p.score !== null ? <circle key={p.key} cx={x} cy={y} r={3.5} fill={BRAND} /> : null;
        })}
        {points.map((p) => {
          const [x, y] = at(p.angle, radius + 26);
          return (
            <text key={p.key} x={x} y={y} textAnchor="middle" dominantBaseline="middle" fontSize="11" fill={TEXT}>
              <tspan x={x} dy="-0.4em">{humanize(p.key)}</tspan>
              <tspan x={x} dy="1.25em" fontWeight="600" fill={p.score === null ? MUTED : TEXT}>
                {p.score === null ? "n/a" : p.score.toFixed(0)}
              </tspan>
            </text>
          );
        })}
      </svg>
      <figcaption className="mt-1 text-center text-[12px] text-[#5d6470]">
        {strongest && weakest
          ? `Strongest: ${humanize(strongest.key)} (${strongest.score!.toFixed(0)}). Weakest: ${humanize(weakest.key)} (${weakest.score!.toFixed(0)}).`
          : "No factors scored yet."}{" "}
        Dashed rings mark 60 and 80.
      </figcaption>
    </figure>
  );
}

export function BudgetWaterfall({ assessment }: { assessment: AssessmentReport }) {
  const figure = (metric: string) => {
    const f = assessment.key_figures.find((k) => k.metric === metric);
    return typeof f?.value === "number" ? f.value : null;
  };
  const income = figure("assessed_net_income");
  const living = figure("assessed_living_expenses");
  const commitments = figure("existing_commitments");
  const repayment = figure("proposed_repayment");
  const surplus = figure("monthly_surplus");

  if (income === null || surplus === null) {
    return <p className="py-10 text-center text-[13px] text-[#8a909a]">Serviceability figures aren&apos;t available for this application.</p>;
  }

  const steps: Step[] = [
    { label: "Net income", value: income, kind: "total" },
    ...(living !== null ? [{ label: "Living costs", value: living, kind: "minus" as const }] : []),
    ...(commitments !== null ? [{ label: "Commitments", value: commitments, kind: "minus" as const }] : []),
    ...(repayment !== null ? [{ label: "New repayment", value: repayment, kind: "minus" as const }] : []),
    { label: "Surplus", value: surplus, kind: "result" },
  ];

  const width = 340;
  const height = 300;
  const top = 24;
  const bottom = 44;
  const plot = height - top - bottom;
  const barW = (width - 20) / steps.length - 14;
  const scale = (v: number) => (Math.max(v, 0) / income) * plot;

  let running = income;
  const bars = steps.map((s, i) => {
    const x = 10 + i * ((width - 20) / steps.length) + 7;
    let y0: number;
    let h: number;
    if (s.kind === "total") {
      h = scale(s.value);
      y0 = top + plot - h;
    } else if (s.kind === "minus") {
      h = scale(s.value);
      y0 = top + plot - scale(running);
      running -= s.value;
    } else {
      h = scale(s.value);
      y0 = top + plot - h;
    }
    const fill = s.kind === "total" ? BRAND : s.kind === "result" ? (s.value >= 0 ? "#2e844a" : "#c23934") : "#b0b6bf";
    return { ...s, x, y0, h: Math.max(h, 1), fill };
  });

  return (
    <figure className="flex flex-col items-center">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full max-w-[340px]" role="img" aria-label="Monthly budget waterfall chart">
        <line x1={0} y1={top + plot} x2={width} y2={top + plot} stroke={GRID} />
        {bars.map((b, i) => (
          <g key={b.label}>
            {i > 0 && bars[i - 1].kind !== "result" && b.kind === "minus" && (
              <line x1={bars[i - 1].x + barW} y1={b.y0} x2={b.x} y2={b.y0} stroke={MUTED} strokeDasharray="3 3" />
            )}
            <rect x={b.x} y={b.y0} width={barW} height={b.h} fill={b.fill} />
            <text x={b.x + barW / 2} y={b.y0 - 6} textAnchor="middle" fontSize="11" fontWeight="600" fill={TEXT}>
              {b.kind === "minus" ? "−" : ""}
              {fmtMoney(b.value)}
            </text>
            <text x={b.x + barW / 2} y={top + plot + 16} textAnchor="middle" fontSize="11" fill={TEXT}>
              {b.label.split(" ").map((word, w) => (
                <tspan key={word} x={b.x + barW / 2} dy={w === 0 ? 0 : "1.2em"}>
                  {word}
                </tspan>
              ))}
            </text>
          </g>
        ))}
      </svg>
      <figcaption className="mt-1 text-center text-[12px] text-[#5d6470]">
        Monthly. {fmtMoney(surplus)} left after the new repayment — {Math.round((surplus / income) * 100)}% of assessed net income.
      </figcaption>
    </figure>
  );
}

// The "add-backs" chain a credit analyst spreads from the financial statements:
// net profit before tax -> + interest expense = EBIT -> + depreciation/amortisation
// = EBITDA, the figure debt service is actually measured against.
export function CashFlowWaterfall({
  netProfit,
  interestExpense,
  ebit,
  depreciation,
  ebitda,
}: {
  netProfit: number | null;
  interestExpense: number | null;
  ebit: number | null;
  depreciation: number | null;
  ebitda: number | null;
}) {
  if (netProfit === null || ebitda === null) {
    return (
      <p className="py-10 text-center text-[13px] text-[#8a909a]">
        Cash-flow add-back figures aren&apos;t available for this application.
      </p>
    );
  }

  const steps: Step[] = [
    { label: "Net profit before tax", value: netProfit, kind: "total" },
    ...(interestExpense !== null ? [{ label: "+ Interest expense", value: interestExpense, kind: "plus" as const }] : []),
    { label: "EBIT", value: ebit ?? netProfit + (interestExpense ?? 0), kind: "result" },
    ...(depreciation !== null ? [{ label: "+ Depreciation", value: depreciation, kind: "plus" as const }] : []),
    { label: "EBITDA", value: ebitda, kind: "result" },
  ];

  const width = 360;
  const height = 300;
  const top = 24;
  const bottom = 44;
  const plot = height - top - bottom;
  const barW = (width - 20) / steps.length - 10;
  // A break-even or loss-making business can have EBITDA <= 0 — guard the
  // scale denominator so bars stay finite instead of NaN/Infinity.
  const scaleMax = Math.max(ebitda, netProfit, 1);
  const scale = (v: number) => (Math.max(v, 0) / scaleMax) * plot;

  let running = 0;
  const bars = steps.map((s, i) => {
    const x = 10 + i * ((width - 20) / steps.length) + 5;
    let y0: number;
    let h: number;
    if (s.kind === "plus") {
      h = scale(s.value);
      y0 = top + plot - scale(running) - h;
      running += s.value;
    } else {
      h = scale(s.value);
      y0 = top + plot - h;
      running = s.value;
    }
    const fill = s.kind === "total" ? BRAND : s.kind === "result" ? "#2e844a" : "#b0b6bf";
    return { ...s, x, y0, h: Math.max(h, 1), fill };
  });

  return (
    <figure className="flex flex-col items-center">
      <svg viewBox={`0 0 ${width} ${height}`} className="h-auto w-full max-w-[360px]" role="img" aria-label="Cash-flow add-back waterfall chart">
        <line x1={0} y1={top + plot} x2={width} y2={top + plot} stroke={GRID} />
        {bars.map((b, i) => (
          <g key={b.label}>
            {i > 0 && b.kind === "plus" && (
              <line x1={bars[i - 1].x + barW} y1={b.y0 + b.h} x2={b.x} y2={b.y0 + b.h} stroke={MUTED} strokeDasharray="3 3" />
            )}
            <rect x={b.x} y={b.y0} width={barW} height={b.h} fill={b.fill} />
            <text x={b.x + barW / 2} y={b.y0 - 6} textAnchor="middle" fontSize="11" fontWeight="600" fill={TEXT}>
              {fmtMoney(b.value)}
            </text>
            <text x={b.x + barW / 2} y={top + plot + 16} textAnchor="middle" fontSize="10.5" fill={TEXT}>
              {b.label.split(" ").map((word, w) => (
                <tspan key={word} x={b.x + barW / 2} dy={w === 0 ? 0 : "1.2em"}>
                  {word}
                </tspan>
              ))}
            </text>
          </g>
        ))}
      </svg>
      <figcaption className="mt-1 text-center text-[12px] text-[#5d6470]">
        EBITDA of {fmtMoney(ebitda)}/year is the cash flow measured against total debt service for DSCR.
      </figcaption>
    </figure>
  );
}
