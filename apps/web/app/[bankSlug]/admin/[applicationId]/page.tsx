"use client";

import { useParams } from "next/navigation";

import { ApplicationDetailView } from "@/components/application-detail";
import { AuthGuard } from "@/components/auth-guard";

export default function AdminApplicationDetailPage() {
  const { bankSlug, applicationId } = useParams<{ bankSlug: string; applicationId: string }>();

  return (
    <AuthGuard allowedRoles={["admin"]}>
      <ApplicationDetailView
        applicationId={applicationId}
        backHref={`/${bankSlug}/admin`}
        backLabel="Back to all applications"
        canAct={false}
      />
    </AuthGuard>
  );
}
