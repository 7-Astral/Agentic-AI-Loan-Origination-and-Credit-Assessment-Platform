"use client";

import { useEffect, useRef, useState } from "react";
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
import { Progress } from "@/components/ui/progress";
import { createConversation, getBank, getConversation, sendConversationMessage } from "@/lib/api";
import type { Bank, LoanType } from "@/lib/types/bank";
import type { ConversationMessage, ConversationStatus } from "@/lib/types/conversation";
import { cn, hexToHslTriplet } from "@/lib/utils";

const BANK_SLUG = "demo-mutual";

const NAV_LINKS = ["Dashboard", "Applications", "Documents", "Support"];

const QUICK_REPLIES = ["What are current rates?", "How much can I borrow?", "Talk to a human"];

const LOAN_OPTIONS: {
  type: LoanType;
  label: string;
  description: string;
  icon: typeof Home;
}[] = [
  {
    type: "home",
    label: "Home Loans",
    description: "Mortgages & refinancing options.",
    icon: Home,
  },
  {
    type: "investment",
    label: "Investment Loans",
    description: "Build your property portfolio.",
    icon: TrendingUp,
  },
  {
    type: "personal",
    label: "Personal Loans",
    description: "Vehicles, renovations, or debt consolidation.",
    icon: User,
  },
  {
    type: "business",
    label: "Business Loans",
    description: "Funding for growth and operations.",
    icon: Building2,
  },
];

// Baseline question set is [employment, income, income_frequency, monthly_expenses,
// existing_debts, existing_debt_amount?, dependents, loan_amount, loan_term_years, ...type-specific].
// "Financial Profile" starts once we're past dependents, i.e. asking loan amount/term/specifics.
const FINANCIAL_PROFILE_START_INDEX = 7;

type PageState = "loading" | "not-found" | "error" | "ready";
type StepStatus = "complete" | "active" | "pending";

function storageKey(slug: string): string {
  return `loan-origination:conversation:${slug}`;
}

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
  const [bank, setBank] = useState<Bank | null>(null);

  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [status, setStatus] = useState<ConversationStatus>("active");
  const [collectedData, setCollectedData] = useState<Record<string, unknown>>({});

  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [isSidebarOpen, setSidebarOpen] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;

    async function init() {
      setPageState("loading");

      let bankData: Bank | null;
      try {
        bankData = await getBank(BANK_SLUG);
      } catch {
        if (!cancelled) setPageState("error");
        return;
      }
      if (cancelled) return;

      if (!bankData) {
        setPageState("not-found");
        return;
      }
      setBank(bankData);

      const key = storageKey(BANK_SLUG);
      const storedId = sessionStorage.getItem(key);

      if (storedId) {
        const resumed = await getConversation(storedId).catch(() => null);
        if (resumed && !cancelled) {
          setConversationId(resumed.id);
          setMessages(resumed.messages);
          setCurrentQuestionIndex(resumed.current_question_index);
          setTotalQuestions(resumed.total_questions);
          setStatus(resumed.status);
          setCollectedData(resumed.collected_data);
          setPageState("ready");
          return;
        }
        sessionStorage.removeItem(key);
      }

      try {
        const created = await createConversation(bankData.id);
        if (cancelled) return;
        sessionStorage.setItem(key, created.conversation_id);
        setConversationId(created.conversation_id);
        setMessages([
          { role: "assistant", content: created.message, created_at: new Date().toISOString() },
        ]);
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
    if (!conversationId || trimmed.length === 0 || isSending || status === "completed") return;

    setMessages((prev) => [
      ...prev,
      { role: "user", content: trimmed, created_at: new Date().toISOString() },
    ]);
    setDraft("");
    setIsSending(true);

    try {
      const result = await sendConversationMessage(conversationId, trimmed);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: result.message, created_at: new Date().toISOString() },
      ]);
      setCurrentQuestionIndex(result.current_question_index);
      setTotalQuestions(result.total_questions);
      setStatus(result.status);
      setCollectedData(result.collected_data);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Sorry, something went wrong sending that. Please try again.",
          created_at: new Date().toISOString(),
        },
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

  if (pageState === "not-found") {
    return (
      <div className="flex h-dvh flex-col items-center justify-center gap-2 p-6 text-center">
        <h1 className="text-xl font-semibold">We couldn&apos;t reach the loan advisor</h1>
        <p className="text-muted-foreground">
          The backend has no bank configured yet. Run the seed script and refresh.
        </p>
      </div>
    );
  }

  if (pageState === "error" || !bank) {
    return (
      <div className="flex h-dvh flex-col items-center justify-center gap-2 p-6 text-center">
        <h1 className="text-xl font-semibold">Something went wrong</h1>
        <p className="text-muted-foreground">Please refresh the page to try again.</p>
      </div>
    );
  }

  const themeStyle = {
    "--primary": hexToHslTriplet(bank.branding.primary_color),
  } as React.CSSProperties;

  const loanTypeKnown = totalQuestions > 0 || status === "completed";
  const showOptions = !loanTypeKnown && !isSending;
  const overallPercent =
    status === "completed"
      ? 100
      : totalQuestions > 0
        ? Math.round((currentQuestionIndex / totalQuestions) * 100)
        : 0;

  const goalsStatus: StepStatus = loanTypeKnown ? "complete" : "active";
  const basicInfoStatus: StepStatus = !loanTypeKnown
    ? "pending"
    : currentQuestionIndex < FINANCIAL_PROFILE_START_INDEX && status !== "completed"
      ? "active"
      : "complete";
  const financialProfileStatus: StepStatus =
    !loanTypeKnown || currentQuestionIndex < FINANCIAL_PROFILE_START_INDEX
      ? "pending"
      : status === "completed"
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

  const progressHelperText =
    status === "completed"
      ? "All done! A loan specialist will review your enquiry."
      : overallPercent === 0
        ? "Let's start by understanding your goals in the chat."
        : "Keep chatting with the AI to complete your enquiry.";

  const collectedEntries = Object.entries(collectedData);

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
        <Progress value={overallPercent} />
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
            LendFlow AI
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
                        <span className="text-muted-foreground">
                          {index === 0
                            ? "Just now"
                            : new Date(message.created_at).toLocaleTimeString()}
                        </span>
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

            {showOptions && (
              <div className="grid grid-cols-1 gap-3 pl-12 sm:grid-cols-2">
                {LOAN_OPTIONS.map((option) => (
                  <button
                    key={option.type}
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
            )}

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
            {status === "completed" ? (
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
                  <button
                    type="button"
                    aria-label="Attach file"
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
