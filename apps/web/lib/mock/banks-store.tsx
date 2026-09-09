"use client";

import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

import { MOCK_BANKS } from "@/lib/mock/admin-data";
import type { AdminBank } from "@/lib/types/admin";

const STORAGE_KEY = "admin:banks";

interface BanksContextValue {
  banks: AdminBank[];
  getBank: (bankId: string) => AdminBank | undefined;
  addBank: (input: { name: string; primaryColor: string; status: AdminBank["status"] }) => AdminBank;
  updateBank: (bankId: string, patch: Partial<Pick<AdminBank, "name" | "primaryColor" | "status">>) => void;
}

const BanksContext = createContext<BanksContextValue | null>(null);

function slugify(name: string): string {
  return (
    name
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "") || "bank"
  );
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function BanksProvider({ children }: { children: ReactNode }) {
  const [banks, setBanks] = useState<AdminBank[]>(MOCK_BANKS);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try {
        setBanks(JSON.parse(raw) as AdminBank[]);
      } catch {
      }
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(banks));
  }, [banks, hydrated]);

  const value: BanksContextValue = {
    banks,
    getBank: (bankId) => banks.find((bank) => bank.id === bankId),
    addBank: (input) => {
      const baseSlug = slugify(input.name);
      let slug = baseSlug;
      let suffix = 2;
      while (banks.some((bank) => bank.id === slug)) {
        slug = `${baseSlug}-${suffix}`;
        suffix += 1;
      }
      const created: AdminBank = { ...input, id: slug, slug, createdAt: todayIso() };
      setBanks((prev) => [...prev, created]);
      return created;
    },
    updateBank: (bankId, patch) => {
      setBanks((prev) => prev.map((bank) => (bank.id === bankId ? { ...bank, ...patch } : bank)));
    },
  };

  return <BanksContext.Provider value={value}>{children}</BanksContext.Provider>;
}

export function useBanks(): BanksContextValue {
  const ctx = useContext(BanksContext);
  if (!ctx) throw new Error("useBanks must be used within BanksProvider");
  return ctx;
}
