import type { ApplicationStatus, Outcome } from "@/lib/types/application";

export type StatusBadgeVariant = "muted" | "outline" | "warning" | "secondary";

// A "decided" status on its own doesn't say which way it was decided — the customer view
// never includes the officer's actual outcome until you open the detail page (see
// services/api/routers/applications.py's `_build_customer_view`), so the list badge for it
// stays neutral rather than guessing at green or red.
export function statusBadgeVariant(status: ApplicationStatus): StatusBadgeVariant {
  switch (status) {
    case "draft":
      return "muted";
    case "submitted":
      return "outline";
    case "in_review":
      return "warning";
    case "decided":
      return "secondary";
  }
}

export function statusLabel(status: ApplicationStatus): string {
  return status.replace(/_/g, " ");
}

export type OutcomeBadgeVariant = "success" | "destructive" | "warning";

export function outcomeBadgeVariant(outcome: Outcome): OutcomeBadgeVariant {
  switch (outcome) {
    case "approved":
      return "success";
    case "rejected":
      return "destructive";
    case "overridden":
      return "warning";
    case "info_requested":
      return "warning";
  }
}

export function outcomeLabel(outcome: Outcome): string {
  switch (outcome) {
    case "approved":
      return "Approved";
    case "rejected":
      return "Rejected";
    case "overridden":
      return "Overridden";
    case "info_requested":
      return "More information requested";
  }
}
