"use client";

import {
  useEffect,
  useRef,
  useState,
  type CSSProperties,
  type FormEvent,
  type ReactNode,
} from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Bot,
  Check,
  FileText,
  Landmark,
  LayoutGrid,
  Lightbulb,
  Loader2,
  Paperclip,
  Send,
  X,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import {
  agentApi,
  AgentApiError,
  type InfoRequest,
  type ProductOption,
  type Progress,
  type RequiredDocument,
  type SlotHint,
  type SubmitResult,
} from "@/lib/agent-api";
import { useToast } from "@/components/ui/Toast";
import { ChatMarkdown } from "@/components/chat/ChatMarkdown";
import { ProductOptionCards } from "@/components/chat/ProductOptionCards";
import {
  DocumentRequestCard,
  type DocCardState,
} from "@/components/chat/DocumentRequestCard";
import { InfoRequestCard } from "@/components/chat/InfoRequestCard";
import { cn } from "@/lib/utils";


type Stage =
  "starting" | "discovery" | "product_selection" | "interview" | "complete";
type Speaker = "loan" | "docs";
type ChatMessage = {
  role: "agent" | "user";
  text: string;
  at: string;
  speaker?: Speaker;
  kind?: "text" | "handover" | "doc";
  docCode?: string;
  products?: ProductOption[];
};
type DocPhase = "off" | "handover" | "active" | "done";
type StepStatus = "complete" | "active" | "pending";

const THEME = {
  "--primary": "165 76% 25%",
  "--primary-foreground": "0 0% 100%",
  "--ring": "165 76% 25%",
} as CSSProperties;

function humanize(key: string) {
  const text = key.replace(/_/g, " ");
  return text.charAt(0).toUpperCase() + text.slice(1);
}

function formatValue(value: unknown): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return value.toLocaleString("en-AU");
  if (value === null || value === undefined || value === "") return "—";
  return humanize(String(value));
}

function inSentence(name: string) {
  return name.charAt(0).toLowerCase() + name.slice(1);
}

function now() {
  return new Date().toISOString();
}

function Pill({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full bg-secondary px-2.5 py-0.5 text-xs font-semibold text-primary",
        className,
      )}
    >
      {children}
    </span>
  );
}

function AgentAvatar({
  speaker = "loan",
  entering = false,
}: {
  speaker?: Speaker;
  entering?: boolean;
}) {
  return (
    <span
      className={cn(
        "flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-white",
        speaker === "docs" ? "bg-cyan-700" : "bg-primary",
        entering && "avatar-in",
      )}
    >
      {speaker === "docs" ? (
        <FileText className="h-5 w-5" aria-hidden="true" />
      ) : (
        <Bot className="h-5 w-5" aria-hidden="true" />
      )}
    </span>
  );
}

function beat(ms: number) {
  const reduce =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  return new Promise((resolve) => setTimeout(resolve, reduce ? 0 : ms));
}

export default function LoanAssistantChat() {
  const { user, token, loading } = useAuth();
  const router = useRouter();
  const { show } = useToast();

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [stage, setStage] = useState<Stage>("starting");
  const [slotsInPlay, setSlotsInPlay] = useState<SlotHint[]>([]);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [productCode, setProductCode] = useState<string | null>(null);
  const [productNames, setProductNames] = useState<Record<string, string>>({});
  const [slotLabels, setSlotLabels] = useState<Record<string, string>>({});
  const [filled, setFilled] = useState<Record<string, unknown>>({});

  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [requiredDocs, setRequiredDocs] = useState<RequiredDocument[] | null>(
    null,
  );
  const [attaching, setAttaching] = useState(false);
  const [docPhase, setDocPhase] = useState<DocPhase>("off");
  const [docStates, setDocStates] = useState<Record<string, DocCardState>>({});
  const [currentDoc, setCurrentDoc] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState("");
  const [dragging, setDragging] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [submitResult, setSubmitResult] = useState<SubmitResult | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [infoRequests, setInfoRequests] = useState<InfoRequest[]>([]);

  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const started = useRef(false);

  useEffect(() => {
    if (!loading && (!user || user.role !== "customer"))
      router.replace("/login");
  }, [loading, user, router]);

  function applyTurn(res: {
    stage: string;
    progress: Progress | null;
    slots_in_play: SlotHint[];
    product_code: string | null;
    products?: ProductOption[] | null;
  }) {
    setStage(res.stage as Stage);
    setProgress(res.progress);
    setSlotsInPlay(res.slots_in_play);
    setProductCode(res.product_code);
    if (res.slots_in_play.length)
      setSlotLabels((prev) => ({
        ...prev,
        ...Object.fromEntries(res.slots_in_play.map((s) => [s.id, s.label])),
      }));
    if (res.products?.length)
      setProductNames((prev) => ({
        ...prev,
        ...Object.fromEntries(
          res.products!.map((p) => [p.product_code, p.name]),
        ),
      }));
  }

  async function beginSession(fresh: boolean) {
    setError(null);
    try {
      if (!fresh) {
        try {
          const requested = new URLSearchParams(window.location.search).get(
            "session",
          );
          const res = requested
            ? await agentApi.resume(token, requested)
            : await agentApi.current(token);
          setSubmitted(!!res.submitted);
          setSessionId(res.session_id);
          applyTurn(res);
          const history: ChatMessage[] = res.messages.map((m) => ({
            role: m.role === "user" ? "user" : "agent",
            text: m.content,
            at: now(),
          }));
          if (res.question)
            history.push({
              role: "agent",
              text: res.question,
              products: res.products ?? undefined,
              at: now(),
            });
          setMessages(history);
          return;
        } catch (err) {
          if (!(err instanceof AgentApiError) || err.status !== 404) throw err;
        }
      }
      const res = await agentApi.start(token);
      setSessionId(res.session_id);
      applyTurn(res);
      setMessages(
        res.question
          ? [
              {
                role: "agent",
                text: res.question,
                products: res.products ?? undefined,
                at: now(),
              },
            ]
          : [],
      );
    } catch (err) {
      setError(
        err instanceof AgentApiError
          ? err.message
          : "Couldn't reach the loan assistant",
      );
    }
  }

  useEffect(() => {
    if (started.current || !user || user.role !== "customer") return;
    started.current = true;
    beginSession(false);
  }, [user]);

  function startOver() {
    if (
      !window.confirm(
        "Start a new application? The one in progress stays saved with the bank's assistant, but this chat will start from the beginning.",
      )
    )
      return;
    setSessionId(null);
    setMessages([]);
    setStage("starting");
    setSlotsInPlay([]);
    setProgress(null);
    setProductCode(null);
    setFilled({});
    setRequiredDocs(null);
    setDocPhase("off");
    setDocStates({});
    setCurrentDoc(null);
    setSubmitResult(null);
    setSubmitted(false);
    setInfoRequests([]);
    router.replace("/customer/chat");
    beginSession(true);
  }

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, sending, requiredDocs, submitResult, infoRequests]);

  const isSubmitted = submitted || !!submitResult;

  useEffect(() => {
    if (!sessionId || !isSubmitted) return;
    let cancelled = false;
    const load = () =>
      agentApi
        .infoRequests(token, sessionId)
        .then((rows) => {
          if (!cancelled) setInfoRequests(rows);
        })
        .catch(() => {});
    load();
    const timer = setInterval(load, 15000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [sessionId, isSubmitted, token]);

  // Put focus back in the reply box after every turn, so the applicant can
 
  useEffect(() => {
    if (!sending && stage !== "complete" && sessionId)
      inputRef.current?.focus();
  }, [sending, stage, sessionId, messages]);

  // Answers collected so far, for the side panel.
  useEffect(() => {
    if (!sessionId || !productCode) return;
    agentApi
      .getApplication(token, sessionId)
      .then((app) => setFilled(app.filled ?? {}))
      .catch(() => {});
  }, [messages, sessionId, productCode, token]);

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
    setMessages((m) => [...m, { role: "user", text, at: now() }]);
    setInput("");
    setSlotsInPlay([]);
    const wasComplete = stage === "complete";
    try {
      const res = await agentApi.sendMessage(token, sessionId, text);
      applyTurn(res);
      if (res.note)
        setMessages((m) => [
          ...m,
          { role: "agent", text: res.note as string, at: now() },
        ]);
      if (res.question)
        setMessages((m) => [
          ...m,
          {
            role: "agent",
            text: res.question as string,
            products: res.products ?? undefined,
            at: now(),
          },
        ]);
      if (res.stage === "complete" && !wasComplete)
        setMessages((m) => [
          ...m,
          {
            role: "agent",
            text:
              docPhase === "off"
                ? "That's everything I need from you for the application. I'll pass you to our Document Assistant to collect a few files."
                : "Thanks — that's everything again. You can submit whenever you're ready.",
            at: now(),
          },
        ]);
    } catch (err) {
      const message =
        err instanceof AgentApiError
          ? err.message
          : "Something went wrong sending that";
      setError(message);
      show(message, "error");
    } finally {
      setSending(false);
    }
  }

  async function refreshDocs() {
    if (!sessionId) return;
    const refreshed = await agentApi.requiredDocuments(token, sessionId);
    setRequiredDocs(refreshed.documents);
  }

  function pushDocs(text: string) {
    setMessages((m) => [
      ...m,
      { role: "agent", speaker: "docs", text, at: now() },
    ]);
  }


  async function askNext(
    lead: string | null,
    docs: RequiredDocument[],
    states: Record<string, DocCardState>,
  ) {
    const outstanding = docs.filter(
      (d) =>
        d.status !== "extracted" &&
        !["received", "skipped"].includes(states[d.code]?.phase ?? ""),
    );
    const next = outstanding[0];
    await beat(500);
    if (!next) {
      setCurrentDoc(null);
      setDocPhase("done");
      pushDocs(
        `${lead ? `${lead} ` : ""}That's all the documents I need. Whenever you're ready, submit your application below.`,
      );
      setAnnouncement(
        "All documents requested. You can submit your application.",
      );
      return;
    }
    if (lead) pushDocs(`${lead} Next up: your ${inSentence(next.name)}.`);
    setDocStates((prev) => ({
      ...prev,
      [next.code]: prev[next.code] ?? { phase: "waiting" },
    }));
    setMessages((m) => [
      ...m,
      {
        role: "agent",
        speaker: "docs",
        kind: "doc",
        docCode: next.code,
        text: "",
        at: now(),
      },
    ]);
    setCurrentDoc(next.code);
    setAnnouncement(`Document Assistant is asking for your ${next.name}.`);
  }


  useEffect(() => {
    if (
      stage !== "complete" ||
      requiredDocs === null ||
      docPhase !== "off" ||
      submitted
    )
      return;
    setDocPhase("handover");
    (async () => {
      await beat(700);
      setMessages((m) => [
        ...m,
        {
          role: "agent",
          speaker: "docs",
          kind: "handover",
          text: "",
          at: now(),
        },
      ]);
      setAnnouncement("The Document Assistant has joined the chat.");
      await beat(900);
      const outstanding = requiredDocs.filter(
        (d) => d.status !== "extracted",
      ).length;
      pushDocs(
        outstanding === 0
          ? "Hi, I'm the Document Assistant. You've already sent everything the bank needs — thank you."
          : `Hi, I'm the Document Assistant. The bank needs ${outstanding} document${outstanding === 1 ? "" : "s"} to verify your application. I'll ask for them one at a time — you can skip any you don't have handy.`,
      );
      setDocPhase("active");
      await askNext(null, requiredDocs, {});
    })();
  }, [stage, requiredDocs, docPhase, submitted]);

  async function replyToRequest(requestId: string, message: string) {
    if (!sessionId) return;
    const updated = await agentApi.replyToInfoRequest(
      token,
      sessionId,
      requestId,
      message,
    );
    setInfoRequests((rows) =>
      rows.map((r) => (r.id === requestId ? { ...r, ...updated } : r)),
    );
    show("Reply sent to the bank", "success");
  }

  async function uploadForRequest(requestId: string, file: File) {
    if (!sessionId) return null;
    const result = await agentApi.uploadForInfoRequest(
      token,
      sessionId,
      requestId,
      file,
    );
    if (result.status === "needs_reupload")
      return (
        result.reason ||
        "That file doesn't look like the document the bank asked for — please try another."
      );
    setInfoRequests(await agentApi.infoRequests(token, sessionId));
    show("Document sent to the bank", "success");
    return null;
  }

  async function handleDocFile(code: string, file: File) {
    if (!sessionId || !requiredDocs) return;
    const doc = requiredDocs.find((d) => d.code === code);
    if (!doc) return;
    setDocStates((prev) => ({
      ...prev,
      [code]: { ...prev[code], phase: "reading", file },
    }));
    setAnnouncement(`Reading your ${doc.name}.`);
    try {
      const result = await agentApi.uploadDocument(
        token,
        sessionId,
        code,
        file,
      );
      if (result.status === "needs_reupload") {
        setDocStates((prev) => ({
          ...prev,
          [code]: {
            phase: "rejected",
            file,
            reason:
              result.reason ||
              `That doesn't look like a ${inSentence(doc.name)} — mind trying another file?`,
            attempt: (prev[code]?.attempt ?? 0) + 1,
          },
        }));
        setAnnouncement(
          `That file wasn't accepted as your ${doc.name}. Please try another.`,
        );
        return;
      }
      const states: Record<string, DocCardState> = {
        ...docStates,
        [code]: { phase: "received", file },
      };
      setDocStates(states);
      setAnnouncement(`${doc.name} received.`);
      refreshDocs().catch(() => {});
      await askNext(
        `Thanks — your ${inSentence(doc.name)} is on file.`,
        requiredDocs,
        states,
      );
    } catch (err) {
      setDocStates((prev) => ({
        ...prev,
        [code]: {
          phase: "rejected",
          file,
          reason:
            err instanceof AgentApiError
              ? err.message
              : "The upload didn't go through — please try again.",
          attempt: (prev[code]?.attempt ?? 0) + 1,
        },
      }));
    }
  }

  async function skipDoc(code: string) {
    if (!requiredDocs) return;
    const states: Record<string, DocCardState> = {
      ...docStates,
      [code]: { phase: "skipped" },
    };
    setDocStates(states);
    await askNext(
      "No problem — you can send it to the bank later.",
      requiredDocs,
      states,
    );
  }

  async function handleQuickAttach(file: File) {
    if (!sessionId) return;
    setAttaching(true);
    try {
      const result = await agentApi.uploadNextDocument(token, sessionId, file);
      if (result.status === "needs_reupload")
        show(
          result.reason ||
            `${file.name} doesn't look right — try a different file`,
          "error",
        );
      else
        show(
          `${result.verification_type.replace(/_/g, " ")} uploaded`,
          "success",
        );
      setMessages((m) => [
        ...m,
        { role: "user", text: `📎 ${file.name}`, at: now() },
        {
          role: "agent",
          text:
            result.status === "needs_reupload"
              ? result.reason ||
                "That document doesn't look right — mind trying a different file?"
              : "Got it, thanks — that's on file.",
          at: now(),
        },
      ]);
      if (stage === "complete") await refreshDocs();
    } catch (err) {
      show(
        err instanceof AgentApiError
          ? err.message
          : "Couldn't attach that file",
        "error",
      );
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
      show("Application submitted — the bank will review it", "success");
    } catch (err) {
      const message =
        err instanceof AgentApiError
          ? err.message
          : "Couldn't submit the application";
      setError(message);
      show(message, "error");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading || !user) return null;


  const interviewShare = progress
    ? progress.answered /
      Math.max(1, progress.answered + progress.remaining_known)
    : 0;
  const docsDone = requiredDocs
    ? requiredDocs.filter((d) => d.status === "extracted").length
    : 0;
  const overall = isSubmitted
    ? 100
    : stage === "complete"
      ? 80 +
        Math.round(
          (requiredDocs?.length ? docsDone / requiredDocs.length : 0) * 15,
        )
      : productCode
        ? 10 + Math.round(interviewShare * 70)
        : stage === "product_selection"
          ? 5
          : 0;

  const currentStep = isSubmitted
    ? 4
    : stage === "complete"
      ? 2
      : productCode
        ? 1
        : 0;
  const steps = [
    {
      title: "Choose your loan",
      description: "Tell the assistant what you need and pick a product.",
    },
    {
      title: "Your details",
      description: "Answer a few questions about you and your finances.",
    },
    {
      title: "Supporting documents",
      description: "Upload payslips, statements and ID.",
    },
    {
      title: "Submit",
      description: "Send your application to the bank for a decision.",
    },
  ];
  const stepStatus = (i: number): StepStatus =>
    i < currentStep ? "complete" : i === currentStep ? "active" : "pending";

  const openRequests = infoRequests.filter((r) => r.status === "open").length;
  const helper = isSubmitted
    ? openRequests > 0
      ? `The bank needs ${openRequests === 1 ? "one more thing" : `${openRequests} more things`} from you.`
      : "All done — the bank has your application."
    : stage === "complete"
      ? requiredDocs?.length
        ? `${docsDone} of ${requiredDocs.length} documents received.`
        : "Upload your documents, then submit when you're ready."
      : productCode
        ? `${progress?.answered ?? 0} answered so far — keep chatting to finish.`
        : "Start by telling the assistant what you're looking for.";

  const collected = Object.entries(filled);
  const productName = productCode
    ? (productNames[productCode] ?? productCode)
    : null;

  const sidebar = (
    <div className="flex flex-col gap-6">
      <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
        <LayoutGrid className="h-5 w-5 text-primary" aria-hidden="true" />
        Application at a Glance
      </h2>

      <div className="rounded-lg border border-slate-200 p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="font-semibold text-slate-900">Overall Progress</span>
          <Pill>{overall}%</Pill>
        </div>
        <div
          className="h-2 w-full overflow-hidden rounded-full bg-secondary"
          role="progressbar"
          aria-valuenow={overall}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${overall}%` }}
          />
        </div>
        <p className="mt-3 text-sm text-slate-500">{helper}</p>
        {productName && (
          <p className="mt-2 text-sm">
            <span className="text-slate-500">Applying for </span>
            <span className="font-medium text-slate-900">{productName}</span>
          </p>
        )}
      </div>

      <div>
        <h3 className="mb-2 border-b border-slate-200 pb-2 font-semibold text-slate-900">
          Next Steps
        </h3>
        <ul className="space-y-4 pt-2">
          {steps.map((step, i) => {
            const status = stepStatus(i);
            return (
              <li key={step.title} className="flex items-start gap-3">
                <span
                  className={cn(
                    "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2",
                    status === "complete" &&
                      "border-primary bg-primary text-primary-foreground",
                    status === "active" && "border-primary",
                    status === "pending" && "border-slate-300",
                  )}
                >
                  {status === "complete" && (
                    <Check className="h-3 w-3" aria-hidden="true" />
                  )}
                  {status === "active" && (
                    <span className="h-2 w-2 rounded-full bg-primary" />
                  )}
                </span>
                <div className={cn(status === "pending" && "opacity-60")}>
                  <p className="text-sm font-semibold text-slate-900">
                    {step.title}
                  </p>
                  <p className="text-sm text-slate-500">{step.description}</p>
                </div>
              </li>
            );
          })}
        </ul>
      </div>

      {collected.length > 0 && (
        <div className="rounded-lg border border-slate-200 p-4">
          <h3 className="mb-3 font-semibold text-slate-900">
            Collected so far
          </h3>
          <dl className="space-y-2 text-sm">
            {collected.map(([key, value]) => (
              <div key={key} className="flex justify-between gap-4">
                <dt className="text-slate-500">
                  {slotLabels[key] ?? humanize(key)}
                </dt>
                <dd className="text-right font-medium text-slate-900">
                  {formatValue(value)}
                </dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      <div className="flex gap-3 rounded-lg bg-secondary p-4 text-sm text-slate-700">
        <Lightbulb
          className="h-4 w-4 shrink-0 text-primary"
          aria-hidden="true"
        />
        <p>
          <span className="font-semibold">Tip:</span> Answer in your own words —
          the assistant works out the details. You can attach documents at any
          time with the paperclip.
        </p>
      </div>
    </div>
  );


  const lastIndex = messages.length - 1;
  const options = slotsInPlay[0]?.options ?? [];
  const canAttach = !!sessionId && !!productCode && !attaching;
  const currentDocName =
    requiredDocs?.find((d) => d.code === currentDoc)?.name ?? "";

  return (
    <div
      className="flex h-dvh flex-col overflow-hidden bg-white text-slate-900"
      style={THEME}
    >
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 px-4 sm:h-16 sm:px-6">
        <div className="flex items-center gap-6">
          {docPhase === "off" ? (
            <span className="flex items-center gap-2 text-lg font-semibold text-primary">
              <Landmark className="h-5 w-5" aria-hidden="true" />
              Loan Assistant
            </span>
          ) : (
            <span
              key="docs"
              className="chat-in flex items-center gap-2 text-lg font-semibold text-cyan-700"
            >
              <FileText className="h-5 w-5" aria-hidden="true" />
              Document Assistant
            </span>
          )}
          <Link
            href="/customer"
            className="hidden items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 sm:flex"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to portal
          </Link>
        </div>
        <div className="flex items-center gap-4">
          <Link
            href="/customer"
            className="text-sm text-slate-500 hover:text-slate-900 sm:hidden"
          >
            Back
          </Link>
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-900 lg:hidden"
          >
            <LayoutGrid className="h-4 w-4" aria-hidden="true" />
            Progress
          </button>
          {sessionId && !isSubmitted && (
            <button
              type="button"
              onClick={startOver}
              className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 transition-colors hover:border-primary hover:text-primary"
            >
              New application
            </button>
          )}
          <span className="hidden text-sm text-slate-500 sm:inline">
            {user.full_name}
          </span>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <div
          className="relative flex min-h-0 flex-1 flex-col"
          onDragOver={(e) => {
            if (docPhase !== "active" || !currentDoc) return;
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={(e) => {
            if (!e.currentTarget.contains(e.relatedTarget as Node | null))
              setDragging(false);
          }}
          onDrop={(e) => {
            if (docPhase !== "active" || !currentDoc) return;
            e.preventDefault();
            setDragging(false);
            const file = e.dataTransfer.files?.[0];
            if (file) handleDocFile(currentDoc, file);
          }}
        >
          <p className="sr-only" aria-live="polite">
            {announcement}
          </p>
          {dragging && currentDoc && (
            <div className="pointer-events-none absolute inset-3 z-10 flex items-center justify-center rounded-xl border-2 border-dashed border-cyan-600 bg-cyan-50/90">
              <p className="text-base font-semibold text-cyan-800">
                Drop to upload your {inSentence(currentDocName)}
              </p>
            </div>
          )}
          <div
            ref={scrollRef}
            className="relative flex-1 space-y-6 overflow-y-auto p-4 sm:p-6"
          >
            {messages.length === 0 && !error && (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Connecting you to the assistant…
              </div>
            )}

            {messages.map((m, i) => {
              if (m.kind === "handover") {
                return (
                  <div
                    key={i}
                    className="chat-in flex items-center gap-3 py-1"
                    role="status"
                  >
                    <span className="divider-in h-px flex-1 bg-slate-200" />
                    <span className="flex items-center gap-2 text-xs font-medium text-slate-500">
                      <FileText
                        className="h-3.5 w-3.5 text-cyan-700"
                        aria-hidden="true"
                      />
                      Document Assistant joined the chat
                    </span>
                    <span className="divider-in h-px flex-1 bg-slate-200" />
                  </div>
                );
              }
              if (m.kind === "doc" && m.docCode) {
                const doc = requiredDocs?.find((d) => d.code === m.docCode);
                if (!doc) return null;
                return (
                  <div key={i} className="sm:pl-[52px]">
                    <DocumentRequestCard
                      doc={doc}
                      state={docStates[doc.code] ?? { phase: "waiting" }}
                      active={currentDoc === doc.code}
                      onFile={(file) => handleDocFile(doc.code, file)}
                      onSkip={() => skipDoc(doc.code)}
                    />
                  </div>
                );
              }
              const docs = m.speaker === "docs";
              const firstFromDocs =
                docs &&
                messages.findIndex(
                  (x) =>
                    x.speaker === "docs" &&
                    x.kind !== "handover" &&
                    x.kind !== "doc",
                ) === i;
              return (
                <div key={i} className="chat-in">
                  {m.role === "agent" ? (
                    <div className="flex gap-3">
                      <AgentAvatar
                        speaker={docs ? "docs" : "loan"}
                        entering={firstFromDocs}
                      />
                      <div className="flex min-w-0 max-w-2xl flex-col gap-2">
                        <div className="flex items-center gap-2 text-xs">
                          {docs ? (
                            <Pill className="bg-cyan-50 text-cyan-800">
                              DOCUMENT ASSISTANT
                            </Pill>
                          ) : (
                            <Pill>LOAN ASSISTANT</Pill>
                          )}
                          <span className="text-slate-400">
                            {new Date(m.at).toLocaleTimeString("en-AU", {
                              hour: "numeric",
                              minute: "2-digit",
                            })}
                          </span>
                        </div>
                        <div className="rounded-lg bg-secondary px-4 py-3 text-sm text-slate-800">
                          <ChatMarkdown text={m.text} />
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="flex justify-end">
                      <div className="max-w-2xl whitespace-pre-wrap rounded-lg bg-primary px-4 py-3 text-sm text-primary-foreground">
                        {m.text}
                      </div>
                    </div>
                  )}
                  {m.products && m.products.length > 0 && (
                    <div className="sm:pl-[52px]">
                      <ProductOptionCards
                        products={m.products}
                        interactive={
                          i === lastIndex &&
                          stage === "product_selection" &&
                          !sending
                        }
                        onSelect={(p) => sendTurn(p.name)}
                      />
                    </div>
                  )}
                </div>
              );
            })}

            {(sending || attaching || docPhase === "handover") && (
              <div className="flex gap-3">
                <AgentAvatar speaker={docPhase === "off" ? "loan" : "docs"} />
                <div className="flex items-center gap-1.5 rounded-lg bg-secondary px-4 py-3 text-sm text-slate-500">
                  {attaching ? (
                    "Reading your document…"
                  ) : (
                    <>
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.3s]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400 [animation-delay:-0.15s]" />
                      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-slate-400" />
                      <span className="sr-only">The assistant is typing</span>
                    </>
                  )}
                </div>
              </div>
            )}

            {docPhase === "done" &&
              stage === "complete" &&
              !isSubmitted &&
              requiredDocs && (
              <div className="chat-in max-w-xl rounded-lg border border-slate-200 p-4 sm:ml-[52px]">
                <h3 className="font-semibold text-slate-900">
                  Ready to submit
                </h3>
                <ul className="mt-2 space-y-1.5 text-sm">
                  {requiredDocs.map((doc) => {
                    const received =
                      doc.status === "extracted" ||
                      docStates[doc.code]?.phase === "received";
                    return (
                      <li
                        key={doc.code}
                        className="flex items-center justify-between gap-3"
                      >
                        <span className="text-slate-700">{doc.name}</span>
                        {received ? (
                          <span className="flex items-center gap-1 text-primary">
                            <Check className="h-4 w-4" aria-hidden="true" />{" "}
                            Received
                          </span>
                        ) : (
                          <span className="text-slate-400">Not provided</span>
                        )}
                      </li>
                    );
                  })}
                </ul>
                <button
                  type="button"
                  onClick={handleSubmitApplication}
                  disabled={submitting}
                  className="mt-4 inline-flex h-10 w-full items-center justify-center gap-2 rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground shadow-sm transition-colors hover:bg-primary/90 disabled:opacity-50"
                >
                  {submitting && (
                    <Loader2
                      className="h-4 w-4 animate-spin"
                      aria-hidden="true"
                    />
                  )}
                  Submit application
                </button>
                <p className="mt-3 text-center text-xs text-slate-500">
                  Have a question about this loan, or need to change an answer
                  first? Type it in the message box below.
                </p>
              </div>
            )}

            {isSubmitted && (
              <div className="rounded-lg border border-slate-200 p-4 sm:ml-[52px]">
                <p className="flex items-center gap-2 font-semibold text-slate-900">
                  <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-primary-foreground">
                    <Check className="h-3.5 w-3.5" aria-hidden="true" />
                  </span>
                  Application submitted
                </p>
                <p className="mt-1 text-sm text-slate-500">
                  A member of the bank&apos;s team reviews every application
                  {submitResult?.pending_position_title ? ` — it's with the ${submitResult.pending_position_title} now` : ""}.
                  We&apos;ll let you know the decision. If they need anything
                  more from you, their request will appear here.
                </p>
                <Link
                  href="/customer"
                  className="mt-3 inline-block text-sm font-medium text-primary hover:underline"
                >
                  Back to my applications
                </Link>
              </div>
            )}

            {isSubmitted &&
              infoRequests.map((r) => (
                <InfoRequestCard
                  key={r.id}
                  request={r}
                  onReply={(message) => replyToRequest(r.id, message)}
                  onFile={(file) => uploadForRequest(r.id, file)}
                />
              ))}

            {error && (
              <p className="text-sm text-red-600 sm:pl-[52px]">{error}</p>
            )}
          </div>

          {docPhase === "active" &&
            currentDoc &&
            docStates[currentDoc]?.phase !== "reading" && (
              <div className="shrink-0 border-t border-slate-200 p-4 sm:p-6">
                <label className="flex cursor-pointer items-center justify-center gap-2 rounded-md border border-slate-300 px-4 py-2.5 text-sm font-medium text-slate-700 transition-colors hover:border-cyan-600 hover:bg-cyan-50 hover:text-cyan-800">
                  <input
                    type="file"
                    accept="image/*,application/pdf"
                    className="sr-only"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleDocFile(currentDoc, file);
                      e.target.value = "";
                    }}
                  />
                  <Paperclip className="h-4 w-4" aria-hidden="true" />
                  Upload your {inSentence(currentDocName)}
                </label>
                <p className="mt-2 text-center text-xs text-slate-400">
                  or drag the file anywhere into the chat
                </p>
              </div>
            )}

          {!isSubmitted && (
            <div className="shrink-0 space-y-3 border-t border-slate-200 p-4 sm:space-y-4 sm:p-6">
              {options.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {options.map((opt) => (
                    <button
                      key={opt}
                      type="button"
                      disabled={sending}
                      onClick={() => sendTurn(opt)}
                      className="rounded-full border border-slate-300 px-4 py-1.5 text-sm text-slate-700 transition-colors hover:border-primary hover:bg-secondary hover:text-primary disabled:opacity-50"
                    >
                      {humanize(opt)}
                    </button>
                  ))}
                </div>
              )}
              <form
                onSubmit={(e: FormEvent) => {
                  e.preventDefault();
                  sendTurn(input);
                }}
                className="flex items-center gap-2"
              >
                <label
                  title={
                    productCode
                      ? "Attach a document"
                      : "Choose a loan product first"
                  }
                  className={cn(
                    "text-slate-400",
                    canAttach
                      ? "cursor-pointer hover:text-primary"
                      : "cursor-not-allowed opacity-40",
                  )}
                >
                  <input
                    type="file"
                    className="hidden"
                    disabled={!canAttach}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) handleQuickAttach(file);
                      e.target.value = "";
                    }}
                  />
                  <Paperclip className="h-5 w-5" aria-hidden="true" />
                  <span className="sr-only">Attach a document</span>
                </label>
                <input
                  ref={inputRef}
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={
                    stage === "complete"
                      ? "Ask about your loan, or tell me what to change..."
                      : "Type your message here..."
                  }
                  disabled={!sessionId || sending}
                  className="flex h-10 w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm placeholder:text-slate-400 focus-visible:border-primary focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                />
                <button
                  type="submit"
                  aria-label="Send message"
                  disabled={!sessionId || sending || input.trim().length === 0}
                  className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
                >
                  <Send className="h-4 w-4" />
                </button>
              </form>
              <p className="text-center text-xs text-slate-400">
                The assistant can make mistakes. The bank checks everything
                before a decision is made.
              </p>
            </div>
          )}
        </div>

        <aside className="hidden w-[360px] shrink-0 flex-col gap-6 overflow-y-auto border-l border-slate-200 p-6 lg:flex">
          {sidebar}
        </aside>
      </div>

      {sidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden" style={THEME}>
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
          <div className="absolute right-0 top-0 flex h-full w-full max-w-sm flex-col gap-6 overflow-y-auto bg-white p-6 shadow-lg">
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              aria-label="Close"
              className="ml-auto text-slate-500 hover:text-slate-900"
            >
              <X className="h-5 w-5" />
            </button>
            {sidebar}
          </div>
        </div>
      )}
    </div>
  );
}
