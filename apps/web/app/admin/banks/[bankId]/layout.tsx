"use client";

import Link from "next/link";
import { notFound, usePathname, useRouter } from "next/navigation";
import { type CSSProperties, type ReactNode } from "react";
import {
  ArrowLeft,
  FileStack,
  LayoutDashboard,
  ListTree,
  Package,
  Scale,
  ScrollText,
  ShieldCheck,
} from "lucide-react";

import { BankSwitcher } from "@/components/admin/bank-switcher";
import { Badge } from "@/components/ui/badge";
import { AdminDataProvider } from "@/lib/mock/admin-store";
import { useBanks } from "@/lib/mock/banks-store";
import { cn, hexToHslTriplet } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "loan-types", label: "Loan Types", icon: ListTree },
  { href: "products", label: "Products", icon: Package },
  { href: "documents", label: "Documents", icon: FileStack },
  { href: "policy", label: "Policy", icon: ShieldCheck },
  { href: "rules", label: "Rules", icon: Scale },
] as const;

const MONITOR_ITEMS = [{ href: "audit", label: "Audit Log", icon: ScrollText }] as const;

export default function BankAdminLayout({
  children,
  params,
}: {
  children: ReactNode;
  params: { bankId: string };
}) {
  const { bankId } = params;
  const pathname = usePathname();
  const router = useRouter();
  const { banks, getBank } = useBanks();

  const bank = getBank(bankId);
  if (!bank) {
    notFound();
  }

  const currentSection = pathname.split(`/banks/${bankId}/`)[1]?.split("/")[0] ?? "dashboard";

  function handleBankChange(nextBankId: string) {
    router.push(`/admin/banks/${nextBankId}/${currentSection}`);
  }

  const themeStyle = { "--primary": hexToHslTriplet(bank.primaryColor) } as CSSProperties;

  return (
    <div className="flex h-dvh" style={themeStyle}>
      <aside className="flex w-64 shrink-0 flex-col border-r border-border bg-secondary/20">
        <div className="border-b border-border p-4">
          <Link
            href="/admin/banks"
            className="mb-4 flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
            All banks
          </Link>
          <BankSwitcher banks={banks} activeBankId={bankId} onSelect={handleBankChange} />
          <Badge variant={bank.status === "active" ? "secondary" : "outline"} className="mt-3">
            {bank.status === "active" ? "Active" : "Draft"}
          </Badge>
        </div>

        <nav className="flex-1 space-y-1 p-3">
          <p className="px-3 pb-1.5 pt-2 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Manage
          </p>
          {NAV_ITEMS.map((item) => {
            const isActive = currentSection === item.href;
            return (
              <Link
                key={item.href}
                href={`/admin/banks/${bankId}/${item.href}`}
                className={cn(
                  "flex items-center gap-2.5 rounded-md border-l-2 border-transparent px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "border-l-primary bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                )}
              >
                <item.icon className="h-4 w-4" aria-hidden="true" />
                {item.label}
              </Link>
            );
          })}

          <p className="px-3 pb-1.5 pt-4 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
            Monitor
          </p>
          {MONITOR_ITEMS.map((item) => {
            const isActive = currentSection === item.href;
            return (
              <Link
                key={item.href}
                href={`/admin/banks/${bankId}/${item.href}`}
                className={cn(
                  "flex items-center gap-2.5 rounded-md border-l-2 border-transparent px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "border-l-primary bg-primary text-primary-foreground shadow-sm"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground",
                )}
              >
                <item.icon className="h-4 w-4" aria-hidden="true" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </aside>

      <div className="min-w-0 flex-1 overflow-y-auto">
        <AdminDataProvider bankId={bankId}>{children}</AdminDataProvider>
      </div>
    </div>
  );
}
