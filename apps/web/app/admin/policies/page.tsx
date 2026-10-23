"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api, type LendingPolicyOut, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { IconShield } from "@/components/icons";

export default function AdminPolicies() {
  const { token } = useAuth();
  const [policies, setPolicies] = useState<LendingPolicyOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    api
      .lendingPolicies(token)
      .then(setPolicies)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
  }, [token]);

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Lending policies</h1>
      <p className="mt-1 text-sm text-slate-500">
        Auto-approval thresholds the Decision Agent checks before approving or escalating.
      </p>

      {error && <div className="mt-4 rounded-lg bg-red-50 px-3.5 py-2.5 text-sm text-red-700">{error}</div>}

      <Card className="mt-6 overflow-hidden">
        <CardHeader title="Active policies" />
        {loading ? (
          <TableSkeleton rows={2} cols={3} />
        ) : policies.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-4 py-14 text-center">
            <IconShield className="h-8 w-8 text-slate-300" />
            <p className="text-sm text-slate-400">No policies yet — run the seed script.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead className="border-b border-slate-100 bg-slate-50/60 text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-5 py-3 font-medium">Auto-approve up to</th>
                  <th className="px-5 py-3 font-medium">Min credit score</th>
                  <th className="px-5 py-3 font-medium">Max DTI ratio</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {policies.map((p) => (
                  <tr key={p.id} className="transition-colors hover:bg-slate-50/60">
                    <td className="px-5 py-3.5 font-medium text-slate-900">
                      ${p.auto_approval_max_amount.toLocaleString()}
                    </td>
                    <td className="px-5 py-3.5 text-slate-600">{p.min_credit_score}</td>
                    <td className="px-5 py-3.5 text-slate-600">{p.max_dti_ratio}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
