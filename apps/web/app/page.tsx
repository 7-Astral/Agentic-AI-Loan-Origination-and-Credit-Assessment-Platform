"use client";

import { useEffect, useState } from "react";

import { checkHealth } from "@/lib/api";

type Status = { state: "loading" } | { state: "ok" } | { state: "error"; message: string };

export default function Home() {
  const [status, setStatus] = useState<Status>({ state: "loading" });

  useEffect(() => {
    checkHealth()
      .then(() => setStatus({ state: "ok" }))
      .catch((error: Error) => setStatus({ state: "error", message: error.message }));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-24">
      <h1 className="text-3xl font-bold">Agentic AI Loan Origination Platform</h1>
      <p className="text-muted-foreground">
        Backend health check: {status.state === "loading" && "checking..."}
        {status.state === "ok" && <span className="text-green-600">passed</span>}
        {status.state === "error" && (
          <span className="text-destructive">failed ({status.message})</span>
        )}
      </p>
    </main>
  );
}
