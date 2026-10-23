import { FileCheck2, Gauge, MessageSquare, UserCheck } from "lucide-react";

const STAGES = [
  { icon: MessageSquare, title: "Intake", sub: "Conversational AI chat", color: "129 140 248" },
  { icon: FileCheck2, title: "Documents", sub: "Collected and verified", color: "56 189 248" },
  { icon: Gauge, title: "Assessment Engine", sub: "Scored by rules, not the LLM", color: "167 139 250" },
  { icon: UserCheck, title: "Staff decision", sub: "A human always decides", color: "52 211 153" },
];

export function AuthShowcase() {
  return (
    <div className="showcase-stage" aria-hidden="true">
      <div className="pipe-tilt">
        <div className="pipe-rail">
          <div className="pipe-packet" />
        </div>
        {STAGES.map((s, i) => (
          <div
            key={s.title}
            className="pipe-step"
            style={{ "--d": `${i * 2}s`, "--c": s.color } as React.CSSProperties}
          >
            <div className="pipe-node">
              <s.icon className="h-4 w-4" />
            </div>
            <div className="pipe-card">
              <p className="text-[13px] font-medium leading-tight text-white">{s.title}</p>
              <p className="mt-0.5 text-[11px] leading-tight text-slate-400">{s.sub}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
