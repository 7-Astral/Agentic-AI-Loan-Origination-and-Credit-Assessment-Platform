"use client";

import { AuthGuard } from "@/components/auth-guard";

export default function AdminPage() {
  return (
    <AuthGuard allowedRoles={["admin"]}>
      <div className="flex flex-1 flex-col items-center justify-center gap-2 p-6 text-center">
        <h1 className="text-xl font-semibold">Admin console</h1>
        <p className="text-muted-foreground">
          Platform administration is coming in a later sprint.
        </p>
      </div>
    </AuthGuard>
  );
}
