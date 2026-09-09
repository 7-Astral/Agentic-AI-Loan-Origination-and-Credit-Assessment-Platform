import type { AdminLoanType, AdminPolicyVersion } from "@/lib/types/admin";
import { cn } from "@/lib/utils";

export function LoanPolicyTable({
  rows,
  loanTypes,
}: {
  rows: AdminPolicyVersion["loanPolicyRows"];
  loanTypes: AdminLoanType[];
}) {
  function categoryLabel(loanTypeCode: string, categoryCode: string) {
    const loanType = loanTypes.find((lt) => lt.code === loanTypeCode);
    return {
      loanTypeName: loanType?.name ?? loanTypeCode,
      categoryName: loanType?.categories.find((c) => c.code === categoryCode)?.name ?? categoryCode,
    };
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-border shadow-sm">
      <table className="w-full min-w-[1100px] text-left text-sm">
        <thead>
          <tr className="border-b border-border bg-secondary/50 text-xs uppercase tracking-wide text-muted-foreground">
            <th className="px-4 py-3 font-medium">Loan type</th>
            <th className="px-3 py-3 font-medium">Min age</th>
            <th className="px-3 py-3 font-medium">Residency</th>
            <th className="px-3 py-3 font-medium">Deposit / LVR</th>
            <th className="px-3 py-3 font-medium">Amount</th>
            <th className="px-3 py-3 font-medium">Term</th>
            <th className="px-3 py-3 font-medium">Income / cash flow</th>
            <th className="px-3 py-3 font-medium">Serviceability</th>
            <th className="px-3 py-3 font-medium">Credit</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => {
            const { loanTypeName, categoryName } = categoryLabel(row.loanTypeCode, row.categoryCode);
            return (
              <tr
                key={`${row.loanTypeCode}-${row.categoryCode}`}
                className={cn("border-b border-border last:border-0", index % 2 === 1 && "bg-secondary/10")}
              >
                <td className="px-4 py-3">
                  <p className="font-medium">{categoryName}</p>
                  <p className="text-xs text-muted-foreground">{loanTypeName}</p>
                </td>
                <td className="px-3 py-3">{row.minAge}</td>
                <td className="px-3 py-3">{row.residencyPolicy}</td>
                <td className="px-3 py-3">{row.depositLvrPolicy}</td>
                <td className="whitespace-nowrap px-3 py-3">{row.loanAmountRange}</td>
                <td className="whitespace-nowrap px-3 py-3">{row.maxTerm}</td>
                <td className="px-3 py-3">{row.incomeCashFlowPolicy}</td>
                <td className="px-3 py-3">{row.serviceabilityPolicy}</td>
                <td className="px-3 py-3">{row.creditPolicy}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
