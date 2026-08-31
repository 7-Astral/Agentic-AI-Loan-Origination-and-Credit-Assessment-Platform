"use client";

import { useEffect, useRef, useState, type ChangeEvent, type CSSProperties } from "react";
import {
  Bell,
  Bot,
  Building2,
  Check,
  Home,
  Landmark,
  LayoutGrid,
  Lightbulb,
  Paperclip,
  Search,
  Send,
  Settings,
  TrendingUp,
  User,
  X,
} from "lucide-react";

import { Avatar } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Progress as ProgressBar } from "@/components/ui/progress";
import {
  checkHealth,
  getApplication,
  listRequiredDocuments,
  sendMessage,
  startApplication,
  uploadNextDocument,
} from "@/lib/api";
import type { Progress, TranscriptMessage } from "@/lib/types/application";
import { cn, hexToHslTriplet } from "@/lib/utils";

const BRAND_COLOR = "#0f4c3a";
const SESSION_STORAGE_KEY = "loan-origination:session";

const NAV_LINKS = ["Dashboard", "Applications", "Documents", "Support"];

const QUICK_REPLIES = ["What are current rates?", "How much can I borrow?", "Talk to a human"];

const LOAN_OPTIONS: {
  label: string;
  description: string;
  icon: typeof Home;
}[] = [
    {
      label: "Home Loans",
      description: "Mortgages & refinancing options.",
      icon: Home,
    },
    {
      label: "Investment Loans",
      description: "Build your property portfolio.",
      icon: TrendingUp,
    },
    {
      label: "Personal Loans",
      description: "Vehicles, renovations, or debt consolidation.",
      icon: User,
    },
    {
      label: "Business Loans",
      description: "Funding for growth and operations.",
      icon: Building2,
    },
  ];

type PageState = "loading" | "error" | "ready";
type StepStatus = "complete" | "active" | "pending";

function prettifyKey(key: string): string {
  const spaced = key.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

function formatValue(value: unknown): string {
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "number") return value.toLocaleString();
  return String(value);
}

export default function ApplyPage() {
  const [pageState, setPageState] = useState<PageState>("loading");

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<TranscriptMessage[]>([]);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [filled, setFilled] = useState<Record<string, unknown>>({});
  const [complete, setComplete] = useState(false);

  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isSidebarOpen, setSidebarOpen] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      setPageState("loading");

      try {
        await checkHealth();
      } catch {
        if (!cancelled) setPageState("error");
        return;
      }
      if (cancelled) return;

      const storedId = sessionStorage.getItem(SESSION_STORAGE_KEY);

      if (storedId) {
        const resumed = await getApplication(storedId).catch(() => null);
        if (resumed && !cancelled) {
          setSessionId(resumed.session_id);
          setMessages(resumed.transcript);
          setProgress(resumed.progress);
          setFilled(resumed.filled);
          setComplete(resumed.progress.complete);
          setPageState("ready");
          return;
        }
        sessionStorage.removeItem(SESSION_STORAGE_KEY);
      }

      try {
        const started = await startApplication();
        if (cancelled) return;
        sessionStorage.setItem(SESSION_STORAGE_KEY, started.session_id);
        setSessionId(started.session_id);
        setMessages(started.question ? [{ role: "assistant", content: started.question }] : []);
        setPageState("ready");
      } catch {
        if (!cancelled) setPageState("error");
      }
    }

    void init();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isSending]);

  async function submitMessage(content: string) {
    const trimmed = content.trim();
    if (!sessionId || trimmed.length === 0 || isSending || complete) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setDraft("");
    setIsSending(true);

    try {
      const result = await sendMessage(sessionId, trimmed);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.question ?? "That's everything I need. Your application is complete.",
        },
      ]);
      setProgress(result.progress);
      setComplete(result.complete);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, something went wrong sending that. Please try again.",
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  async function handleFileSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !sessionId || isSending) return;

    setMessages((prev) => [...prev, { role: "user", content: `?? ${file.name}` }]);
    setIsSending(true);

    try {
      const result = await uploadNextDocument(sessionId, file);
      const text =
        result.status === "extracted"
          ? "Thanks - that's been received and processed."
          : result.status === "needs_reupload"
            ? `That doesn't look right. ${result.reason ?? ""}`.trim()
            : "Received.";
      setMessages((prev) => [...prev, { role: "assistant", content: text }]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: error instanceof Error ? error.message : "Sorry, that upload didn't go through.",
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  async function handleAttachClick() {
    if (!sessionId || isSending) return;

    setIsSending(true);
    try {
      const required = await listRequiredDocuments(sessionId);
      const next = required.find((d) => d.status === "not_uploaded" || d.status === "needs_reupload");
      if (!next) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "All required documents have already been provided." },
        ]);
        return;
      }

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `Please attach your ${next.name.toLowerCase()}.` },
      ]);
      fileInputRef.current?.click();
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Couldn't check required documents. Please try again." },
      ]);
    } finally {
      setIsSending(false);
    }
  }
  if (pageState === "loading") {
    return (
      <div className="flex h-dvh items-center justify-center text-muted-foreground">Loading...</div>
    );
  }

  if (pageState === "error") {
    return (
      <div className="flex h-dvh flex-col items-center justify-center gap-2 p-6 text-center">
        <h1 className="text-xl font-semibold">Something went wrong</h1>
        <p className="text-muted-foreground">Please refresh the page to try again.</p>
      </div>
    );
  }

  const themeStyle = {
    "--primary": hexToHslTriplet(BRAND_COLOR),
  } as CSSProperties;

  const loanTypeKnown = progress !== null || complete;
  const showOptions = !loanTypeKnown && !isSending;
  const totalKnown = progress ? progress.answered + progress.remaining_known : 0;
  const overallPercent = complete ? 100 : totalKnown > 0 ? Math.round((progress!.answered / totalKnown) * 100) : 0;

  const currentPhase = progress?.current_phase ?? null;

  const goalsStatus: StepStatus = loanTypeKnown ? "complete" : "active";
  const basicInfoStatus: StepStatus = !loanTypeKnown
    ? "pending"
    : complete || (currentPhase !== null && currentPhase > 2)
      ? "complete"
      : "active";
  const financialProfileStatus: StepStatus = !loanTypeKnown || (currentPhase !== null && currentPhase <= 2)
    ? "pending"
    : complete
      ? "complete"
      : "active";

  const steps: { id: string; title: string; description: string; status: StepStatus }[] = [
    {
      id: "goals",
      title: "Understanding your goals",
      description: "Chat with AI to define your loan needs.",
      status: goalsStatus,
    },
    {
      id: "basic-info",
      title: "Basic Information",
      description: "Provide contact and demographic details.",
      status: basicInfoStatus,
    },
    {
      id: "financial-profile",
      title: "Financial Profile",
      description: "Connect accounts or upload documents.",
      status: financialProfileStatus,
    },
  ];

  const progressHelperText = complete
    ? "All done! A loan specialist will review your enquiry."
    : overallPercent === 0
      ? "Let's start by understanding your goals in the chat."
      : "Keep chatting with the AI to complete your enquiry.";

  const collectedEntries = Object.entries(filled);

  const sidebarContent = (
    <div className="flex flex-col gap-6">
      <h2 className="flex items-center gap-2 text-lg font-semibold">
        <LayoutGrid className="h-5 w-5 text-primary" aria-hidden="true" />
        Application at a Glance
      </h2>

      <div className="rounded-lg border border-border p-4">
        <div className="mb-2 flex items-center justify-between">
          <span className="font-semibold">Overall Progress</span>
          <Badge variant="secondary" className="text-primary">
            {overallPercent}%
          </Badge>
        </div>
        <ProgressBar value={overallPercent} />
        <p className="mt-3 text-sm text-muted-foreground">{progressHelperText}</p>
      </div>

      <div>
        <h3 className="mb-2 border-b border-border pb-2 font-semibold">Next Steps</h3>
        <ul className="space-y-4 pt-2">
          {steps.map((step) => (
            <li key={step.id} className="flex items-start gap-3">
              <span
                className={cn(
                  "mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full border-2",
                  step.status === "complete" && "border-primary bg-primary text-primary-foreground",
                  step.status === "active" && "border-primary",
                  step.status === "pending" && "border-input",
                )}
              >
                {step.status === "complete" && <Check className="h-3 w-3" aria-hidden="true" />}
                {step.status === "active" && <span className="h-2 w-2 rounded-full bg-primary" />}
              </span>
              <div className={cn(step.status === "pending" && "opacity-60")}>
                <p className="text-sm font-semibold">{step.title}</p>
                <p className="text-sm text-muted-foreground">{step.description}</p>
              </div>
            </li>
          ))}
        </ul>
      </div>

      {collectedEntries.length > 0 && (
        <div className="rounded-lg border border-border p-4">
          <h3 className="mb-3 font-semibold">Collected so far</h3>
          <dl className="space-y-2 text-sm">
            {collectedEntries.map(([key, value]) => (
              <div key={key} className="flex justify-between gap-4">
                <dt className="text-muted-foreground">{prettifyKey(key)}</dt>
                <dd className="font-medium">{formatValue(value)}</dd>
              </div>
            ))}
          </dl>
        </div>
      )}

      <div className="flex gap-3 rounded-lg bg-secondary/60 p-4 text-sm">
        <Lightbulb className="h-4 w-4 shrink-0 text-primary" aria-hidden="true" />
        <p>
          <span className="font-semibold">Tip:</span> The more details you share with the AI, the
          faster we can match you with the right loan products.
        </p>
      </div>
    </div>
  );

  return (
    <div className="flex h-dvh flex-col" style={themeStyle}>
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border px-4 sm:h-16 sm:px-6">
        <div className="flex items-center gap-8">
          <span className="flex items-center gap-2 text-lg font-semibold text-primary">
            <Landmark className="h-5 w-5" aria-hidden="true" />
            LendFlowq AI
          </span>
          <nav className="hidden items-center gap-6 md:flex">
            {NAV_LINKS.map((link, index) => (
              <a
                key={link}
                href="#"
                className={cn(
                  "border-b-2 border-transparent pb-0.5 text-sm",
                  index === 0
                    ? "border-primary font-medium text-primary"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {link}
              </a>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3 sm:gap-4">
          <button
            type="button"
            onClick={() => setSidebarOpen(true)}
            aria-label="View application progress"
            className="text-muted-foreground hover:text-foreground lg:hidden"
          >
            <LayoutGrid className="h-5 w-5" />
          </button>
          <button
            type="button"
            aria-label="Search"
            className="hidden text-muted-foreground hover:text-foreground sm:block"
          >
            <Search className="h-5 w-5" />
          </button>
          <button
            type="button"
            aria-label="Notifications"
            className="hidden text-muted-foreground hover:text-foreground sm:block"
          >
            <Bell className="h-5 w-5" />
          </button>
          <button
            type="button"
            aria-label="Settings"
            className="hidden text-muted-foreground hover:text-foreground sm:block"
          >
            <Settings className="h-5 w-5" />
          </button>
          <Avatar className="bg-secondary text-secondary-foreground">
            <User className="h-5 w-5" aria-hidden="true" />
          </Avatar>
        </div>
      </header>

      <div className="flex min-h-0 flex-1">
        <div className="flex min-h-0 flex-1 flex-col">
          <div ref={scrollRef} className="flex-1 space-y-6 overflow-y-auto p-4 sm:p-6">
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`}>
                {message.role === "assistant" ? (
                  <div className="flex gap-3">
                    <Avatar className="bg-primary text-primary-foreground">
                      <Bot className="h-5 w-5" aria-hidden="true" />
                    </Avatar>
                    <div className="flex max-w-2xl flex-col gap-2">
                      <div className="flex items-center gap-2 text-xs">
                        <Badge variant="secondary" className="text-primary">
                          VERIFIED AI
                        </Badge>
                      </div>
                      <div className="rounded-lg bg-secondary px-4 py-3 text-sm text-secondary-foreground">
                        {message.content}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-end">
                    <div className="max-w-2xl rounded-lg bg-primary px-4 py-3 text-sm text-primary-foreground">
                      {message.content}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {/* {showOptions && (
              <div className="grid grid-cols-1 gap-3 pl-12 sm:grid-cols-2">
                {LOAN_OPTIONS.map((option) => (
                  <button
                    key={option.label}
                    type="button"
                    onClick={() => void submitMessage(`I'm interested in ${option.label}`)}
                    className="flex flex-col items-start gap-2 rounded-lg border border-border bg-background p-4 text-left transition-colors hover:border-primary hover:bg-secondary/50"
                  >
                    <option.icon className="h-5 w-5 text-muted-foreground" aria-hidden="true" />
                    <span className="font-semibold">{option.label}</span>
                    <span className="text-sm text-muted-foreground">{option.description}</span>
                  </button>
                ))}
              </div>
            )} */}

            {isSending && (
              <div className="flex gap-3">
                <Avatar className="bg-primary text-primary-foreground">
                  <Bot className="h-5 w-5" aria-hidden="true" />
                </Avatar>
                <div className="rounded-lg bg-secondary px-4 py-3 text-sm text-muted-foreground">
                  Thinking...
                </div>
              </div>
            )}
          </div>

          <div className="shrink-0 space-y-3 border-t border-border p-4 sm:space-y-4 sm:p-6">
            {complete ? (
              <p className="text-center text-sm text-muted-foreground">
                This enquiry is complete. A loan specialist will be in touch.
              </p>
            ) : (
              <>
                <div className="flex flex-wrap gap-2">
                  {QUICK_REPLIES.map((reply) => (
                    <button
                      key={reply}
                      type="button"
                      onClick={() => void submitMessage(reply)}
                      className="rounded-full border border-input px-4 py-1.5 text-sm hover:bg-secondary"
                    >
                      {reply}
                    </button>
                  ))}
                </div>
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    void submitMessage(draft);
                  }}
                  className="flex items-center gap-2"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/*,.pdf"
                    className="hidden"
                    onChange={handleFileSelected}
                  />
                  <button
                    type="button"
                    aria-label="Attach file"
                    onClick={() => void handleAttachClick()}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <Paperclip className="h-5 w-5" />
                  </button>
                  <input
                    value={draft}
                    onChange={(event) => setDraft(event.target.value)}
                    placeholder="Type your message here..."
                    disabled={isSending}
                    className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                  />
                  <button
                    type="submit"
                    aria-label="Send message"
                    disabled={isSending || draft.trim().length === 0}
                    className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground disabled:opacity-50"
                  >
                    <Send className="h-4 w-4" />
                  </button>
                </form>
                <p className="text-center text-xs text-muted-foreground">
                  LendFlow AI can make mistakes. Consider verifying important financial information.
                </p>
              </>
            )}
          </div>
        </div>

        <aside className="hidden w-[360px] shrink-0 flex-col gap-6 overflow-y-auto border-l border-border p-6 lg:flex">
          {sidebarContent}
        </aside>
      </div>

      {isSidebarOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
          <div className="absolute right-0 top-0 flex h-full w-full max-w-sm flex-col gap-6 overflow-y-auto bg-background p-6 shadow-lg">
            <button
              type="button"
              onClick={() => setSidebarOpen(false)}
              aria-label="Close"
              className="ml-auto text-muted-foreground hover:text-foreground"
            >
              <X className="h-5 w-5" />
            </button>
            {sidebarContent}
          </div>
        </div>
      )}
    </div>
  );
}
