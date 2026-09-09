"use client";

import { Check, ChevronsUpDown, Landmark } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { AdminBank } from "@/lib/types/admin";
import { cn } from "@/lib/utils";

export function BankSwitcher({
  banks,
  activeBankId,
  onSelect,
}: {
  banks: AdminBank[];
  activeBankId: string;
  onSelect: (bankId: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const active = banks.find((bank) => bank.id === activeBankId);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        aria-haspopup="listbox"
        aria-expanded={open}
        className="flex w-full items-center gap-2.5 rounded-lg border border-input bg-background px-2.5 py-2 text-left shadow-sm transition-colors hover:bg-secondary/60"
      >
        <span
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-white"
          style={{ backgroundColor: active?.primaryColor ?? "#64748b" }}
        >
          <Landmark className="h-4 w-4" aria-hidden="true" />
        </span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold leading-tight">
            {active?.name ?? "Select bank"}
          </span>
          <span className="block truncate text-xs text-muted-foreground">/{active?.slug}</span>
        </span>
        <ChevronsUpDown className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      </button>

      {open && (
        <div
          role="listbox"
          className="absolute left-0 right-0 top-full z-20 mt-1.5 max-h-72 overflow-y-auto rounded-lg border border-border bg-background p-1 shadow-lg"
        >
          {banks.map((bank) => (
            <button
              key={bank.id}
              type="button"
              role="option"
              aria-selected={bank.id === activeBankId}
              onClick={() => {
                onSelect(bank.id);
                setOpen(false);
              }}
              className={cn(
                "flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-left text-sm hover:bg-secondary",
                bank.id === activeBankId && "bg-secondary/70",
              )}
            >
              <span
                className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ backgroundColor: bank.primaryColor }}
                aria-hidden="true"
              />
              <span className="min-w-0 flex-1 truncate">{bank.name}</span>
              {bank.id === activeBankId && (
                <Check className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
