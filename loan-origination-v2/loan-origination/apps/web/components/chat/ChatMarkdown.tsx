import React from "react";

/**
 * A small, dependency-free renderer for the loan assistant's replies. The
 * interaction agent (services/agent-backend) is an LLM and naturally lists
 * things out — e.g. presenting several loan products, or reading the
 * applicant's figures back to them at confirmation — so its replies often
 * contain **bold**, `- ` / `1. ` lists, and multiple lines. Rendering that
 * as one flat string prints the markdown syntax literally and collapses the
 * line breaks. This turns it into real paragraphs/lists/emphasis instead,
 * without pulling in a markdown package for what is a narrow, known shape
 * of output (short chat replies, not arbitrary documents).
 */

function renderInline(text: string, keyPrefix: string): React.ReactNode[] {
  const pattern = /(\*\*[^*\n]+\*\*|`[^`\n]+`|\*[^*\n]+\*|_[^_\n]+_)/g;
  return text
    .split(pattern)
    .filter((part) => part.length > 0)
    .map((part, i) => {
      const key = `${keyPrefix}-${i}`;
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={key} className="font-semibold">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code key={key} className="rounded bg-slate-100 px-1 py-0.5 text-[0.85em]">
            {part.slice(1, -1)}
          </code>
        );
      }
      if ((part.startsWith("*") && part.endsWith("*")) || (part.startsWith("_") && part.endsWith("_"))) {
        return <em key={key}>{part.slice(1, -1)}</em>;
      }
      return <React.Fragment key={key}>{part}</React.Fragment>;
    });
}

function listKind(line: string): "ul" | "ol" | null {
  if (/^\s*[-*]\s+/.test(line)) return "ul";
  if (/^\s*\d+[.)]\s+/.test(line)) return "ol";
  return null;
}

function stripMarker(line: string): string {
  return line.replace(/^\s*[-*]\s+/, "").replace(/^\s*\d+[.)]\s+/, "");
}

export function ChatMarkdown({ text }: { text: string }) {
  const blocks = text.trim().split(/\n{2,}/);

  return (
    <div className="space-y-2">
      {blocks.map((block, bi) => {
        const lines = block.split("\n").filter((l) => l.trim().length > 0);
        if (lines.length === 0) return null;

        const kinds = lines.map(listKind);
        if (kinds.every((k) => k === "ul")) {
          return (
            <ul key={bi} className="list-disc space-y-1 pl-5">
              {lines.map((line, li) => (
                <li key={li}>{renderInline(stripMarker(line), `${bi}-${li}`)}</li>
              ))}
            </ul>
          );
        }
        if (kinds.every((k) => k === "ol")) {
          return (
            <ol key={bi} className="list-decimal space-y-1 pl-5">
              {lines.map((line, li) => (
                <li key={li}>{renderInline(stripMarker(line), `${bi}-${li}`)}</li>
              ))}
            </ol>
          );
        }
        return (
          <p key={bi} className="leading-relaxed">
            {lines.map((line, li) => (
              <React.Fragment key={li}>
                {li > 0 && <br />}
                {renderInline(line, `${bi}-${li}`)}
              </React.Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}
