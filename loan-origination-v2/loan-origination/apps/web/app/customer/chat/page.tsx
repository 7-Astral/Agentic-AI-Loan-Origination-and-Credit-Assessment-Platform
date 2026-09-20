"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import {
  agentApi,
  AgentApiError,
  type ProductOption,
  type Progress,
  type RequiredDocument,
  type SlotHint,
  type SubmitResult,
} from "@/lib/agent-api";
import { useToast } from "@/components/ui/Toast";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { IconArrowRight, IconCheck, IconClipboard, IconPaperclip, IconSparkle } from "@/components/icons";
import { ChatMarkdown } from "@/components/chat/ChatMarkdown";
import { ProductOptionCards } from "@/components/chat/ProductOptionCards";

type ChatMessage = { role: "agent" | "user"; text: string; products?: ProductOption[] };

export default function LoanAssistantChat() {
  const { user, token, loading } = useAuth();
  const router = useRouter();
  const { show } = useToast();

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [stage, setStage] = useState<"starting" | "discovery" | "product_selection" | "interview" | "complete">(
    "starting"
  );
  const [slotsInPlay, setSlotsInPlay] = useState<SlotHint[]>([]);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [productCode, setProductCode] = useState<string | null>(null);

  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [requiredDocs, setRequiredDocs] = useState<RequiredDocument[] | null>(null);
  const [uploadingCode, setUploadingCode] = useState<string | null>(null);
  const [attaching, setAttaching] = useState(false);

  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<SubmitResult | null>(null);

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const started = useRef(false);

  useEffect(() => {
    if (!loading && (!user || user.role !== "customer")) router.replace("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (started.current || !user || user.role !== "customer") return;
    started.current = true;
    agentApi
      .start(token)
      .then((res) => {
        setSessionId(res.session_id);
        setStage(res.stage as typeof stage);
        setProgress(res.progress);
        setSlotsInPlay(res.slots_in_play);
        setProductCode(res.product_code);
        if (res.question)
          setMessages([{ role: "agent", text: res.question, products: res.products ?? undefined }]);
      })
      .catch((err) => {
        const message = err instanceof AgentApiError ? err.message : "Couldn't reach the loan assistant";
        setError(message);
      });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, stage]);

  // Put focus back in the reply box after every turn — the agent's reply
  // (or the initial question) lands, the input re-enables, and the
  // applicant can just keep typing instead of having to click into it again.
  useEffect(() => {
    if (!sending && stage !== "complete" && sessionId) {
      inputRef.current?.focus();
    }
  }, [sending, stage, sessionId, messages]);

  useEffect(() => {
    if (stage !== "complete" || !sessionId) return;
    agentApi
      .requiredDocuments(token, sessionId)
      .then((res) => setRequiredDocs(res.documents))
      .catch(() => setRequiredDocs([]));
  }, [stage, sessionId, token]);

  async function sendTurn(text: string) {
    if (!sessionId || !text.trim() || sending) return;
    setError(null);
    setSending(true);
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setSlotsInPlay([]);
    try {
      const res = await agentApi.sendMessage(token, sessionId, text);
      setStage(res.stage as typeof stage);
      setProgress(res.progress);
      setSlotsInPlay(res.slots_in_play);
      setProductCode(res.product_code);
      if (res.question)
        setMessages((m) => [
          ...m,
          { role: "agent", text: res.question as string, products: res.products ?? undefined },
        ]);
      if (res.stage === "complete" && !res.question) {
        setMessages((m) => [
          ...m,
          { role: "agent", text: "That's everything I need for the interview. Let's look at documents next." },
        ]);
      }
    } catch (err) {
      const message = err instanceof AgentApiError ? err.message : "Something went wrong sending that";
      setError(message);
      show(message, "error");
    } finally {
      setSending(false);
    }
  }

  function handleSubmitTurn(e: FormEvent) {
    e.preventDefault();
    sendTurn(input);
  }

  function selectProduct(p: ProductOption) {
    sendTurn(p.name);
  }

  async function handleUpload(doc: RequiredDocument, file: File) {
    if (!sessionId) return;
    setUploadingCode(doc.code);
    try {
      const result = await agentApi.uploadDocument(token, sessionId, doc.code, file);
      if (result.status === "needs_reupload") {
        show(result.reason || `${doc.name} doesn't look right — try a different file`, "error");
      } else {
        show(`${doc.name} uploaded`, "success");
      }
      const refreshed = await agentApi.requiredDocuments(token, sessionId);
      setRequiredDocs(refreshed.documents);
    } catch (err) {
      const message = err instanceof AgentApiError ? err.message : "Upload failed";
      show(message, "error");
    } finally {
      setUploadingCode(null);
    }
  }

  async function handleQuickAttach(file: File) {
    if (!sessionId) return;
    setAttaching(true);
    try {
      const result = await agentApi.uploadNextDocument(token, sessionId, file);
      if (result.status === "needs_reupload") {
        show(result.reason || `${file.name} doesn't look right — try a different file`, "error");
      } else {
        show(`${result.verification_type.replace(/_/g, " ")} uploaded`, "success");
      }
      setMessages((m) => [
        ...m,
        { role: "user", text: `📎 ${file.name}` },
        {
          role: "agent",
          text:
            result.status === "needs_reupload"
              ? result.reason || "That document doesn't look right — mind trying a different file?"
              : "Got it, thanks — that's on file.",
        },
      ]);
      if (stage === "complete") {
        const refreshed = await agentApi.requiredDocuments(token, sessionId);
        setRequiredDocs(refreshed.documents);
      }
    } catch (err) {
      const message = err instanceof AgentApiError ? err.message : "Couldn't attach that file";
      show(message, "error");
    } finally {
      setAttaching(false);
    }
  }

  async function handleSubmitApplication() {
    if (!sessionId) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await agentApi.submit(token, sessionId);
      setSubmitResult(result);
      show(
        result.outcome === "auto_approved" ? "Your loan was auto-approved!" : "Application submitted for review",
        "success"
      );
    } catch (err) {
      const message = err instanceof AgentApiError ? err.message : "Couldn't submit the application";
      setError(message);
      show(message, "error");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading || !user) return null;

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:py-10">
      <div className="mx-auto max-w-3xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-600 text-white">
              <IconSparkle className="h-5 w-5" />
            </div>
            <div>
              <h1 className="text-lg font-semibold tracking-tight text-slate-900">Loan assistant</h1>
              <p className="text-xs text-slate-400">Talk through your application instead of filling a form</p>
            </div>
          </div>
          <Link href="/customer" className="text-sm font-medium text-indigo-600 hover:text-indigo-500">
            Back to portal
          </Link>
        </div>

        {progress && (
          <div className="mt-5">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>{productCode ? `Applying for ${productCode}` : "Finding the right product"}</span>
              <span>{progress.answered} answered</span>
            </div>
            <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
              <div
                className="h-full rounded-full bg-indigo-600 transition-all"
                style={{
                  width: `${Math.min(
                    100,
                    Math.round((progress.answered / Math.max(1, progress.answered + progress.remaining_known)) * 100)
                  )}%`,
                }}
              />
            </div>
          </div>
        )}

        <Card className="mt-5 flex h-[28rem] flex-col overflow-hidden">
          <div ref={scrollRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
            {messages.length === 0 && !error && (
              <p className="text-sm text-slate-400">Connecting you to the assistant…</p>
            )}
            {messages.map((m, i) => (
              <div key={i}>
                <div className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[85%] rounded-2xl px-3.5 py-2.5 text-sm ${
                      m.role === "user"
                        ? "bg-indigo-600 text-white"
                        : "border border-slate-200 bg-white text-slate-800"
                    }`}
                  >
                    {m.role === "agent" ? (
                      <ChatMarkdown text={m.text} />
                    ) : (
                      <span className="whitespace-pre-wrap">{m.text}</span>
                    )}
                  </div>
                </div>
                {m.products && m.products.length > 0 && (
                  <ProductOptionCards
                    products={m.products}
                    interactive={i === messages.length - 1 && stage === "product_selection" && !sending}
                    onSelect={selectProduct}
                  />
                )}
              </div>
            ))}
            {sending && (
              <div className="flex justify-start">
                <div className="flex items-center gap-1 rounded-2xl border border-slate-200 bg-white px-3.5 py-2.5">
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-300 [animation-delay:-0.3s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-300 [animation-delay:-0.15s]" />
                  <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-300" />
                </div>
              </div>
            )}
            {error && <p className="text-sm text-red-600">{error}</p>}
          </div>

          {slotsInPlay.some((s) => s.options && s.options.length > 0) && (
            <div className="flex flex-wrap gap-2 border-t border-slate-100 px-4 py-3">
              {slotsInPlay[0]?.options?.map((opt) => (
                <button
                  key={opt}
                  type="button"
                  disabled={sending}
                  onClick={() => sendTurn(opt)}
                  className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 transition-colors hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 disabled:opacity-50"
                >
                  {opt}
                </button>
              ))}
            </div>
          )}

          {stage !== "complete" && (
            <form onSubmit={handleSubmitTurn} className="flex items-center gap-2 border-t border-slate-100 p-3">
              <label
                title={productCode ? "Attach a document" : "Choose a loan product first"}
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-slate-300 text-slate-500 transition-colors ${
                  !sessionId || !productCode || attaching
                    ? "cursor-not-allowed opacity-40"
                    : "cursor-pointer hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-600"
                }`}
              >
                <input
                  type="file"
                  className="hidden"
                  disabled={!sessionId || !productCode || attaching}
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) handleQuickAttach(file);
                    e.target.value = "";
                  }}
                />
                <IconPaperclip className="h-4.5 w-4.5" />
              </label>
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={!sessionId || sending}
                placeholder="Type your reply…"
                className="flex-1 rounded-lg border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 placeholder:text-slate-400 focus:border-indigo-500 focus:outline-none focus:ring-4 focus:ring-indigo-500/10 disabled:opacity-50"
              />
              <Button type="submit" disabled={!sessionId || sending || !input.trim()}>
                <IconArrowRight className="h-4 w-4" />
              </Button>
            </form>
          )}
        </Card>

        {stage === "complete" && !submitResult && (
          <Card className="mt-5 p-5">
            <div className="flex items-center gap-2">
              <IconClipboard className="h-4 w-4 text-slate-400" />
              <h2 className="text-sm font-semibold text-slate-900">Supporting documents</h2>
            </div>
            <p className="mt-1 text-sm text-slate-500">
              Upload what you have — you can still submit without every document if you&apos;d rather sort it out
              with a staff member afterwards.
            </p>

            {requiredDocs === null ? (
              <div className="mt-4 space-y-2">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div key={i} className="h-12 animate-pulse rounded-lg bg-slate-100" />
                ))}
              </div>
            ) : (
              <ul className="mt-4 divide-y divide-slate-100">
                {requiredDocs.map((doc) => (
                  <li key={doc.code} className="flex items-center justify-between gap-3 py-3">
                    <div>
                      <p className="text-sm font-medium text-slate-800">{doc.name}</p>
                      <p className="mt-0.5 text-xs text-slate-400">
                        {doc.status === "not_uploaded"
                          ? "Not uploaded"
                          : doc.status === "needs_reupload"
                            ? "Doesn't match — try again"
                            : doc.verification === "mismatch"
                              ? "Uploaded — details don't quite match what you told us"
                              : "Uploaded"}
                      </p>
                    </div>
                    <label className="shrink-0">
                      <input
                        type="file"
                        className="hidden"
                        disabled={uploadingCode === doc.code}
                        onChange={(e) => {
                          const file = e.target.files?.[0];
                          if (file) handleUpload(doc, file);
                          e.target.value = "";
                        }}
                      />
                      <span
                        className={`inline-flex cursor-pointer items-center gap-1.5 rounded-lg border px-3 py-1.5 text-xs font-medium transition-colors ${
                          doc.status === "extracted"
                            ? "border-emerald-200 bg-emerald-50 text-emerald-700"
                            : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                        } ${uploadingCode === doc.code ? "opacity-50" : ""}`}
                      >
                        {doc.status === "extracted" ? (
                          <>
                            <IconCheck className="h-3.5 w-3.5" /> Uploaded
                          </>
                        ) : uploadingCode === doc.code ? (
                          "Uploading…"
                        ) : (
                          "Choose file"
                        )}
                      </span>
                    </label>
                  </li>
                ))}
              </ul>
            )}

            <Button onClick={handleSubmitApplication} loading={submitting} className="mt-5 w-full">
              Review and submit application
              <IconArrowRight className="h-4 w-4" />
            </Button>
          </Card>
        )}

        {submitResult && (
          <Card className="mt-5 p-5">
            <div className="flex items-start gap-2.5 rounded-lg border border-emerald-200 bg-emerald-50 px-3.5 py-3 text-sm text-emerald-800">
              <IconCheck className="mt-0.5 h-4 w-4 shrink-0" />
              <span>
                {submitResult.outcome === "auto_approved" ? (
                  <>Your application was auto-approved.</>
                ) : (
                  <>
                    Submitted — now under review
                    {submitResult.pending_position_title ? ` by the ${submitResult.pending_position_title}` : ""}.
                  </>
                )}
              </span>
            </div>
            <div className="mt-3 flex items-center gap-2">
              <Badge tone={submitResult.outcome === "auto_approved" ? "emerald" : "amber"}>
                {submitResult.status.replace(/_/g, " ")}
              </Badge>
            </div>
            <Link href="/customer">
              <Button variant="secondary" className="mt-4 w-full">
                Back to my applications
              </Button>
            </Link>
          </Card>
        )}
      </div>
    </main>
  );
}
