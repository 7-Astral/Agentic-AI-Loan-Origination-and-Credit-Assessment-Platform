"use client";

import { useParams } from "next/navigation";

import { ApplicationQueue } from "@/components/application-queue";
import { AuthGuard } from "@/components/auth-guard";

export default function OfficerQueuePage() {
  const { bankSlug } = useParams<{ bankSlug: string }>();

  return (
    <AuthGuard allowedRoles={["loan_officer", "credit_manager"]}>
      <ApplicationQueue title="Application queue" basePath={`/${bankSlug}/officer`} />
    </AuthGuard>
  );
}
