"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type LoanApplicationOut } from "@/lib/api";
import { Modal } from "@/components/ui/Modal";
import { Button } from "@/components/ui/Button";
import { useToast } from "@/components/ui/Toast";
import { IconCheck, IconClose } from "@/components/icons";

// Approve / reject dialog for an escalated application — used from the
// applications list and from the application report.
export function DecideModal({
  application,
  token,
  onClose,
  onDecided,
}: {
  application: LoanApplicationOut | null;
  token: string | null;
  onClose: () => void;
  onDecided: () => void;
}) {
  const { show } = useToast();
  const [reason, setReason] = useState("");
  const [deciding, setDeciding] = useState<"approved" | "rejected" | null>(null);

  useEffect(() => {
    if (application) setReason("");
  }, [application]);

  async function submit(decision: "approved" | "rejected") {
    if (!token || !application) return;
    setDeciding(decision);
    try {
      await api.decideApplication(token, application.id, { decision, reason: reason || undefined });
      show(decision === "approved" ? "Application approved" : "Application rejected", "success");
      onClose();
      onDecided();
    } catch (err) {
      show(err instanceof ApiError ? err.message : "Couldn't record that decision", "error");
    } finally {
      setDeciding(null);
    }
  }

  return (
    <Modal open={application !== null} onClose={onClose} title="Decide application">
      {application && (
        <div>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
            <dt className="text-slate-400">Customer</dt>
            <dd className="text-slate-800">{application.applicant_name ?? "—"}</dd>
            <dt className="text-slate-400">Type</dt>
            <dd className="capitalize text-slate-800">{application.loan_type}</dd>
            <dt className="text-slate-400">Amount</dt>
            <dd className="font-medium text-slate-900">${application.requested_amount.toLocaleString()}</dd>
            <dt className="text-slate-400">Pending on</dt>
            <dd className="text-slate-800">{application.pending_position_title ?? "—"}</dd>
          </dl>

          <label htmlFor="decide-reason" className="mt-4 block text-xs font-medium text-slate-500">
            Reason (optional)
          </label>
          <textarea
            id="decide-reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            placeholder="Notes for the record — shared with the applicant"
            className="mt-1.5 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-4 focus:ring-indigo-500/10"
          />

          <div className="mt-4 flex gap-2">
            <Button
              onClick={() => submit("approved")}
              loading={deciding === "approved"}
              disabled={deciding !== null}
              className="flex-1"
            >
              <IconCheck className="h-4 w-4" />
              Approve
            </Button>
            <Button
              variant="danger"
              onClick={() => submit("rejected")}
              loading={deciding === "rejected"}
              disabled={deciding !== null}
              className="flex-1"
            >
              <IconClose className="h-4 w-4" />
              Reject
            </Button>
          </div>
        </div>
      )}
    </Modal>
  );
}
