"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowRight, Landmark, Plus } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogFooter, Field } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { useBanks } from "@/lib/mock/banks-store";

const COLOR_PRESETS = ["#0f4c3a", "#1d4ed8", "#7c2d12", "#7c3aed", "#be123c", "#0e7490"];

export default function BanksPage() {
  const router = useRouter();
  const { banks, addBank } = useBanks();

  const [isCreateOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [primaryColor, setPrimaryColor] = useState(COLOR_PRESETS[0]);

  function handleCreate() {
    const trimmed = name.trim();
    if (!trimmed) return;
    const created = addBank({ name: trimmed, primaryColor, status: "draft" });
    setCreateOpen(false);
    setName("");
    setPrimaryColor(COLOR_PRESETS[0]);
    router.push(`/admin/banks/${created.id}/dashboard`);
  }

  return (
    <div className="min-h-dvh bg-secondary/20">
      <div className="mx-auto max-w-5xl px-6 py-10 sm:px-10">
        <div className="mb-8 flex items-center justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              LendFlow Admin
            </p>
            <h1 className="text-2xl font-semibold tracking-tight">Banks</h1>
            <p className="mt-1 text-sm text-muted-foreground">
              Choose a bank to manage its loan types, products, documents, policy and rules.
            </p>
          </div>
          <Button onClick={() => setCreateOpen(true)}>
            <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
            New bank
          </Button>
        </div>

        {banks.length === 0 ? (
          <div className="flex flex-col items-center rounded-xl border border-dashed border-input bg-background py-16 text-center">
            <Landmark className="mb-3 h-8 w-8 text-muted-foreground" aria-hidden="true" />
            <p className="font-medium">No banks yet</p>
            <p className="mt-1 max-w-sm text-sm text-muted-foreground">
              Create your first bank to start configuring loan types, products and policy.
            </p>
            <Button className="mt-4" onClick={() => setCreateOpen(true)}>
              <Plus className="mr-2 h-4 w-4" aria-hidden="true" />
              New bank
            </Button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {banks.map((bank) => (
              <Link
                key={bank.id}
                href={`/admin/banks/${bank.id}/dashboard`}
                className="group relative flex items-start gap-4 overflow-hidden rounded-xl border border-border bg-background p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/50 hover:shadow-md"
              >
                <span
                  className="absolute inset-x-0 top-0 h-1"
                  style={{ backgroundColor: bank.primaryColor }}
                  aria-hidden="true"
                />
                <span
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-white"
                  style={{ backgroundColor: bank.primaryColor }}
                >
                  <Landmark className="h-5 w-5" aria-hidden="true" />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <h2 className="truncate font-semibold">{bank.name}</h2>
                    <Badge variant={bank.status === "active" ? "secondary" : "outline"} className="shrink-0">
                      {bank.status === "active" ? "Active" : "Draft"}
                    </Badge>
                  </div>
                  <p className="mt-0.5 text-sm text-muted-foreground">/{bank.slug}</p>
                  <p className="mt-3 text-xs text-muted-foreground">Created {bank.createdAt}</p>
                </div>
                <ArrowRight
                  className="mt-1 h-4 w-4 shrink-0 text-muted-foreground opacity-0 transition-opacity group-hover:opacity-100"
                  aria-hidden="true"
                />
              </Link>
            ))}
          </div>
        )}
      </div>

      <Dialog
        open={isCreateOpen}
        onClose={() => setCreateOpen(false)}
        title="New bank"
        description="Add a bank to start configuring its loan products and policy."
      >
        <form
          onSubmit={(event) => {
            event.preventDefault();
            handleCreate();
          }}
          className="space-y-4"
        >
          <Field label="Bank name" htmlFor="bank-name">
            <Input
              id="bank-name"
              value={name}
              onChange={(event) => setName(event.target.value)}
              placeholder="e.g. Coastal Community Bank"
              autoFocus
            />
          </Field>

          <Field label="Brand color" hint="Used to accent this bank's admin area and applicant-facing pages.">
            <div className="flex flex-wrap items-center gap-2">
              {COLOR_PRESETS.map((color) => (
                <button
                  key={color}
                  type="button"
                  onClick={() => setPrimaryColor(color)}
                  aria-label={`Use color ${color}`}
                  className="h-7 w-7 rounded-full ring-offset-2 ring-offset-background transition-shadow"
                  style={{
                    backgroundColor: color,
                    boxShadow: primaryColor === color ? `0 0 0 2px ${color}` : undefined,
                  }}
                />
              ))}
              <input
                type="color"
                value={primaryColor}
                onChange={(event) => setPrimaryColor(event.target.value)}
                aria-label="Custom brand color"
                className="h-7 w-9 cursor-pointer rounded border border-input bg-transparent p-0.5"
              />
            </div>
          </Field>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => setCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={name.trim().length === 0}>
              Create bank
            </Button>
          </DialogFooter>
        </form>
      </Dialog>
    </div>
  );
}
