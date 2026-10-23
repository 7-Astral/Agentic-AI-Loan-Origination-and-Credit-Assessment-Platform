"use client";

import { useStaff } from "@/lib/staff-context";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { IconBell, IconCheck } from "@/components/icons";

export default function StaffNotifications() {
  const { notifications, loading, markNotificationRead } = useStaff();

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Notifications</h1>
      <p className="mt-1 text-sm text-slate-500">
        Alerts sent to you when a loan application needs your approval, based on your position.
      </p>

      <Card className="mt-6 overflow-hidden">
        <CardHeader title="Recent" subtitle={`${notifications.length} total`} />
        {loading ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-14 animate-pulse rounded-lg bg-slate-100" />
            ))}
          </div>
        ) : notifications.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-4 py-14 text-center">
            <IconBell className="h-8 w-8 text-slate-300" />
            <p className="text-sm text-slate-400">No notifications yet.</p>
          </div>
        ) : (
          <ul className="divide-y divide-slate-100">
            {notifications.map((n) => (
              <li key={n.id} className={`flex items-start justify-between gap-4 px-5 py-4 ${n.is_read ? "" : "bg-sky-50/40"}`}>
                <div className="flex items-start gap-3">
                  <div
                    className={`mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${
                      n.is_read ? "bg-slate-100 text-slate-400" : "bg-sky-100 text-sky-600"
                    }`}
                  >
                    <IconBell className="h-4 w-4" />
                  </div>
                  <div>
                    <p className={`text-sm ${n.is_read ? "text-slate-600" : "font-medium text-slate-900"}`}>
                      {n.title}
                    </p>
                    <p className="mt-0.5 text-sm text-slate-500">{n.message}</p>
                    <p className="mt-1 text-xs text-slate-400">{new Date(n.created_at).toLocaleString()}</p>
                  </div>
                </div>
                {!n.is_read && (
                  <Button variant="secondary" onClick={() => markNotificationRead(n.id)} className="shrink-0">
                    <IconCheck className="h-4 w-4" />
                    Mark read
                  </Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
