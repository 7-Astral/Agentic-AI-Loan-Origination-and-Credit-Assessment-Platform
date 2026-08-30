"use client";

import { useEffect, useRef, useState } from "react";
import { PhaseRail } from "@/components/PhaseRail";
import { sendMessage, startApplication, type TurnResponse } from "@/lib/api";

type Message = { role: "agent" | "you"; text: string };

export default function Page() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [turn, setTurn] = useState<TurnResponse | null>(null);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    startApplication()
      .then((res) => {
        setTurn(res);
        if (res.question) setMessages([{ role: "agent", text: res.question }]);
      })
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function submit() {
    const text = input.trim();
    if (!text || !turn || busy) return;

    setMessages((m) => [...m, { role: "you", text }]);
    setInput("");
    setBusy(true);
    setError(null);

    try {
      const res = await sendMessage(turn.session_id, text);
      setTurn(res);
      if (res.question) {
        setMessages((m) => [...m, { role: "agent", text: res.question! }]);
      } else {
        setMessages((m) => [
          ...m,
          {
            role: "agent",
            text: "That's everything I need. Your application is complete.",
          },
        ]);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  const chips = turn?.slots_in_play?.find((s) => s.options)?.options ?? [];
  const done = turn?.complete ?? false;

  return (
    <main className="flex h-dvh flex-col">
      <header className="border-b border-rule px-5 py-4">
        <div className="mx-auto flex max-w-3xl items-baseline justify-between">
          <span className="font-voice text-lg">Mutualdata</span>
          {turn?.progress && (
            <span className="text-xs text-muted tabular-nums">
              {turn.progress.answered} of{" "}
              {turn.progress.answered + turn.progress.remaining_known} answered
            </span>
          )}
        </div>
      </header>

      <PhaseRail
        stage={turn?.stage ?? "discovery"}
        currentPhase={turn?.progress?.current_phase ?? null}
      />

      <div className="flex-1 overflow-y-auto px-5">
        <div className="mx-auto flex max-w-3xl flex-col gap-7 py-9">
          {messages.map((m, i) =>
            m.role === "agent" ? (
              <div key={i} className="rise max-w-[46rem]">
                <div className="mb-2.5 h-px w-8 bg-eucalypt" aria-hidden />
                <p className="font-voice text-[19px] leading-[1.65] whitespace-pre-line">
                  {m.text}
                </p>
              </div>
            ) : (
              <div key={i} className="rise flex justify-end">
                <p className="max-w-[34rem] rounded-2xl bg-eucalypt px-4 py-2.5 text-[15px] leading-relaxed text-paper">
                  {m.text}
                </p>
              </div>
            ),
          )}

          {busy && (
            <p className="text-sm text-muted" role="status">
              Thinking…
            </p>
          )}

          {error && (
            <p className="text-sm text-[#8c2f2f]" role="alert">
              {error}. Check the backend is running, then try again.
            </p>
          )}

          <div ref={endRef} />
        </div>
      </div>

      <div className="border-t border-rule bg-paper px-5 py-4">
        <div className="mx-auto max-w-3xl">
          {chips.length > 0 && !busy && !done && (
            <div className="mb-3 flex flex-wrap gap-2">
              {chips.map((opt) => (
                <button
                  key={opt}
                  onClick={() => setInput(opt.replace(/_/g, " "))}
                  className="rounded-full border border-rule bg-eucalypt-soft px-3 py-1 text-xs text-eucalypt transition hover:border-eucalypt"
                >
                  {opt.replace(/_/g, " ")}
                </button>
              ))}
            </div>
          )}

          <div className="flex items-end gap-3">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit();
                }
              }}
              rows={1}
              disabled={busy || done}
              placeholder={done ? "Application complete" : "Type your answer"}
              aria-label="Your answer"
              className="max-h-40 flex-1 resize-none rounded-xl border border-rule bg-white px-4 py-3 text-[15px] leading-relaxed placeholder:text-muted focus:border-eucalypt focus:outline-none disabled:bg-transparent"
            />
            <button
              onClick={submit}
              disabled={busy || done || !input.trim()}
              className="rounded-xl bg-eucalypt px-5 py-3 text-[15px] font-medium text-paper transition disabled:opacity-35"
            >
              Send
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}