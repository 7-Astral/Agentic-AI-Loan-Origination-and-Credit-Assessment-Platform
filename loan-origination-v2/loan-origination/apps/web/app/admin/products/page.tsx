"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { api, type LoanProductOut, ApiError } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { IconPackage } from "@/components/icons";

export default function AdminProducts() {
  const { token } = useAuth();
  const [products, setProducts] = useState<LoanProductOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return;
    api
      .loanProducts(token)
      .then(setProducts)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Failed to load"));
  }, [token]);

  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Loan products</h1>
      <p className="mt-1 text-sm text-slate-500">Products available across banks on the platform.</p>

      {error && <div className="mt-4 rounded-lg bg-red-50 px-3.5 py-2.5 text-sm text-red-700">{error}</div>}

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {products === null &&
          Array.from({ length: 3 }).map((_, i) => (
            <Card key={i} className="p-5">
              <Skeleton className="h-9 w-9 rounded-xl" />
              <Skeleton className="mt-4 h-4 w-2/3" />
              <Skeleton className="mt-3 h-3 w-full" />
              <Skeleton className="mt-2 h-3 w-3/4" />
            </Card>
          ))}

        {products?.map((p) => (
          <Card key={p.id} className="p-5">
            <div className="flex items-start justify-between gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                <IconPackage className="h-5 w-5" />
              </div>
              <Badge tone="slate">{p.product_type}</Badge>
            </div>
            <h2 className="mt-3 font-semibold text-slate-900">{p.name}</h2>
            <dl className="mt-3 space-y-1.5 text-sm">
              <div className="flex justify-between">
                <dt className="text-slate-400">Amount</dt>
                <dd className="font-medium text-slate-700">
                  ${p.min_amount.toLocaleString()} – ${p.max_amount.toLocaleString()}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-400">Rate</dt>
                <dd className="font-medium text-slate-700">
                  {p.interest_rate_min}% – {p.interest_rate_max}%
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-slate-400">Tenure</dt>
                <dd className="font-medium text-slate-700">
                  {p.tenure_min_months}–{p.tenure_max_months} mo
                </dd>
              </div>
            </dl>
          </Card>
        ))}

        {products?.length === 0 && (
          <p className="text-sm text-slate-400">No products yet — run the seed script.</p>
        )}
      </div>
    </div>
  );
}
