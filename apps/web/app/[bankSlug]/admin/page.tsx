"use client";

import { useParams } from "next/navigation";

import { ApplicationQueue } from "@/components/application-queue";
import { AuthGuard } from "@/components/auth-guard";

export default function AdminPage() {
  const { bankSlug } = useParams<{ bankSlug: string }>();

  return (
    <AuthGuard allowedRoles={["admin"]}>
      <ApplicationQueue
        title="All applications (platform-wide oversight)"
        basePath={`/${bankSlug}/admin`}
      />
    </AuthGuard>
  );
}
