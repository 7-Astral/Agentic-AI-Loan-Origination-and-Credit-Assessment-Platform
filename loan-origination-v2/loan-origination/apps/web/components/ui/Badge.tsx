const ROLE_STYLES: Record<string, string> = {
  admin: "bg-violet-50 text-violet-700 ring-1 ring-inset ring-violet-600/20",
  staff: "bg-sky-50 text-sky-700 ring-1 ring-inset ring-sky-600/20",
  customer: "bg-emerald-50 text-emerald-700 ring-1 ring-inset ring-emerald-600/20",
};

export function RoleBadge({ role }: { role: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium capitalize ${
        ROLE_STYLES[role] ?? "bg-slate-100 text-slate-600 ring-1 ring-inset ring-slate-500/10"
      }`}
    >
      {role}
    </span>
  );
}

export function Badge({
  children,
  tone = "slate",
}: {
  children: React.ReactNode;
  tone?: "slate" | "indigo" | "emerald" | "amber" | "red";
}) {
  const tones: Record<string, string> = {
    slate: "bg-slate-100 text-slate-600 ring-slate-500/10",
    indigo: "bg-indigo-50 text-indigo-700 ring-indigo-600/20",
    emerald: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
    amber: "bg-amber-50 text-amber-700 ring-amber-600/20",
    red: "bg-red-50 text-red-700 ring-red-600/20",
  };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${tones[tone]}`}>
      {children}
    </span>
  );
}
