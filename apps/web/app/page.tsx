import Link from "next/link";
import { IconArrowRight, IconShield, IconSparkle, IconUsers } from "@/components/icons";

const FEATURES = [
  {
    icon: IconSparkle,
    title: "AI-assisted intake",
    desc: "Conversational agents collect applicant details and match eligible loan products automatically.",
  },
  {
    icon: IconShield,
    title: "Bank-grade compliance",
    desc: "Encrypted sensitive fields, immutable assessment audit trail, and full activity logging.",
  },
  {
    icon: IconUsers,
    title: "Three role-gated portals",
    desc: "Purpose-built experiences for customers, bank staff, and platform admins.",
  },
];

export default function Home() {
  return (
    <main className="relative min-h-screen overflow-hidden bg-slate-50">
      <div className="absolute inset-0 bg-grid-slate [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,black,transparent)]" />

      <div className="relative mx-auto flex min-h-screen max-w-5xl flex-col items-center justify-center px-4 py-16 text-center sm:px-6">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-indigo-200 bg-indigo-50 px-3 py-1 text-xs font-medium text-indigo-700">
          <IconSparkle className="h-3.5 w-3.5" />
          Agentic AI Loan Origination
        </span>

        <h1 className="mt-6 max-w-2xl text-4xl font-semibold tracking-tight text-slate-900 sm:text-5xl">
          Loan origination, run by agents.
        </h1>
        <p className="mt-4 max-w-xl text-base text-slate-500 sm:text-lg">
          End-to-end loan origination and credit assessment — from conversational
          intake to automated approval, with human escalation when it matters.
        </p>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row">
          <Link
            href="/login"
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-6 py-3 text-sm font-medium text-white shadow-sm shadow-indigo-600/20 transition-colors hover:bg-indigo-500"
          >
            Sign in
            <IconArrowRight className="h-4 w-4" />
          </Link>
          <Link
            href="/register"
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 bg-white px-6 py-3 text-sm font-medium text-slate-700 transition-colors hover:bg-slate-50"
          >
            Create an account
          </Link>
        </div>

        <div className="mt-20 grid w-full grid-cols-1 gap-4 text-left sm:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-2xl border border-slate-200 bg-white/70 p-5 backdrop-blur-sm">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600">
                <f.icon className="h-5 w-5" />
              </div>
              <h3 className="mt-3 text-sm font-semibold text-slate-900">{f.title}</h3>
              <p className="mt-1 text-sm text-slate-500">{f.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}
