import { IconShield, IconSparkle, IconUsers } from "./icons";

const POINTS = [
  { icon: IconSparkle, text: "Conversational AI intake across every loan type" },
  { icon: IconShield, text: "Encrypted PII and a full compliance audit trail" },
  { icon: IconUsers, text: "Dedicated portals for customers, staff and admins" },
];

export function AuthShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="flex min-h-screen bg-slate-50">
      {/* Branding panel — hidden on small screens */}
      <div className="relative hidden w-[42%] flex-col justify-between overflow-hidden bg-slate-900 p-10 text-white lg:flex">
        <div className="absolute inset-0 bg-grid-slate opacity-[0.04]" />
        <div className="absolute -left-24 -top-24 h-72 w-72 rounded-full bg-indigo-500/20 blur-3xl" />
        <div className="absolute -bottom-24 -right-16 h-72 w-72 rounded-full bg-violet-500/20 blur-3xl" />

        <div className="relative">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-white/15 bg-white/5 px-3 py-1 text-xs font-medium">
            <IconSparkle className="h-3.5 w-3.5" />
            Loan Origination Platform
          </span>
          <h1 className="mt-6 text-3xl font-semibold leading-tight">
            Agentic AI loan origination and credit assessment.
          </h1>
        </div>

        <ul className="relative space-y-4">
          {POINTS.map((p) => (
            <li key={p.text} className="flex items-start gap-3">
              <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10">
                <p.icon className="h-4 w-4" />
              </div>
              <p className="text-sm text-slate-300">{p.text}</p>
            </li>
          ))}
        </ul>
      </div>

      {/* Form panel */}
      <div className="flex flex-1 items-center justify-center px-4 py-10 sm:px-6">
        <div className="w-full max-w-sm">{children}</div>
      </div>
    </main>
  );
}
