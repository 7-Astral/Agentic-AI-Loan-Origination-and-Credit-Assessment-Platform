"use client";

const PHASES = [
  { n: 0, label: "Your goal" },
  { n: 1, label: "About you" },
  { n: 2, label: "The loan" },
  { n: 3, label: "Work & income" },
  { n: 4, label: "Your finances" },
  { n: 5, label: "The details" },
  { n: 6, label: "Consent" },
  { n: 7, label: "Review" },
];

export function PhaseRail({
  stage,
  currentPhase,
}: {
  stage: string;
  currentPhase: number | null;
}) {
  const active =
    stage === "discovery" || stage === "product_selection"
      ? 0
      : stage === "complete"
        ? 7
        : (currentPhase ?? 1);

  return (
    <nav aria-label="Application progress" className="border-b border-rule">
      <ol className="mx-auto flex max-w-3xl gap-1 overflow-x-auto px-5 py-3">
        {PHASES.map((phase) => {
          const done = phase.n < active;
          const now = phase.n === active;
          return (
            <li key={phase.n} className="flex min-w-fit flex-1 flex-col gap-1.5">
              <span
                aria-hidden
                className={`h-[3px] rounded-full transition-colors duration-500 ${
                  done
                    ? "bg-eucalypt"
                    : now
                      ? "bg-eucalypt/45"
                      : "bg-rule"
                }`}
              />
              <span
                className={`text-[11px] tracking-wide whitespace-nowrap transition-colors ${
                  now ? "text-eucalypt font-medium" : "text-muted"
                }`}
              >
                {phase.label}
              </span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}