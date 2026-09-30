import type { ReactNode } from "react";

// The playground pages were built against shadcn-style tokens; this scope
// gives them their own background and border colour without touching the
// rest of the app's styling.
export default function PlaygroundLayout({ children }: { children: ReactNode }) {
  return <div className="playground-scope min-h-screen bg-background text-foreground">{children}</div>;
}
