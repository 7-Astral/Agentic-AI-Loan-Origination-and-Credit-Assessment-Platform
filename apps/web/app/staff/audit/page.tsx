"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { useStaff } from "@/lib/staff-context";
import { api, type AuditLogOut, ApiError } from "@/lib/api";
import { Card, CardHeader } from "@/components/ui/Card";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { IconFile, IconLock } from "@/components/icons";

export default function StaffAudit() {
  const { token } = useAuth();
  const { position, loading: staffLoading } = useStaff();
  const [logs, setLogs] = useState<AuditLogOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isManager = !!position && position.can_manage_staff && position.can_manage_products;

  useEffect(() => {
    if (!token || !isManager) return;
    api
      .bankAuditLogs(token)
      .then(setLogs)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, isManager]);

  if (!staffLoading && !isManager) {
    return (
      <Card className="mt-6 flex flex-col items-center gap-2 p-10 text-center">
        <IconLock className="h-8 w-8 text-slate-300" />
        <h1 className="text-sm font-semibold text-slate-900">Restricted</h1>
        <p className="text-sm text-slate-400">
          Only your bank&apos;s manager (a position with both staff and product management) can view the audit
          log.
        </p>
      </Card>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Audit log</h1>
      <p className="mt-1 text-sm text-slate-500">
        Most recent 200 recorded actions for your bank — staff, products, policies and application decisions.
      </p>

      {error && <div className="mt-4 rounded-lg bg-red-50 px-3.5 py-2.5 text-sm text-red-700">{error}</div>}

      <Card className="mt-6 overflow-hidden">
        <CardHeader title="Recent activity" />
        {loading ? (
          <TableSkeleton rows={4} cols={3} />
        ) : logs.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-4 py-14 text-center">
            <IconFile className="h-8 w-8 text-slate-300" />
            <p className="text-sm text-slate-400">No audit entries yet — they&apos;ll appear as your bank is used.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead className="border-b border-slate-100 bg-slate-50/60 text-xs uppercase tracking-wide text-slate-400">
                <tr>
                  <th className="px-5 py-3 font-medium">When</th>
                  <th className="px-5 py-3 font-medium">Entity</th>
                  <th className="px-5 py-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {logs.map((l) => (
                  <tr key={l.id} className="transition-colors hover:bg-slate-50/60">
                    <td className="px-5 py-3.5 text-slate-500">{new Date(l.created_at).toLocaleString()}</td>
                    <td className="px-5 py-3.5">
                      <span className="font-medium text-slate-700 capitalize">{l.entity_type.replace(/_/g, " ")}</span>{" "}
                      <span className="text-slate-400">
                        {l.entity_label ?? `#${l.entity_id.slice(0, 8)}`}
                      </span>
                    </td>
                    <td className="px-5 py-3.5">
                      <Badge tone="indigo">{l.action.replace(/_/g, " ")}</Badge>
                    </td>
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
