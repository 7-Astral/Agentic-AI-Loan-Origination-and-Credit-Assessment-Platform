"use client";

import type { Box } from "@/lib/types/documents";
import { cn } from "@/lib/utils";

export type StagePage = {
  imageUrl: string | null;
  iframeUrl: string | null;
  width: number;
  height: number;
  fields: Record<string, Box>;
  rows: Record<number, Box>;
};

export type ScanPhase = "idle" | "scanning" | "done";

type Props = {
  pages: StagePage[];
  phase: ScanPhase;
  looping: boolean;
  sweepMs: number;
  revealed: ReadonlySet<string>;
  activeId: string | null;
};

const PAD_RATIO = 0.005;

function place(box: Box, page: StagePage) {
  const padX = page.width * PAD_RATIO;
  const padY = padX;
  return {
    left: `${((box.x - padX) / page.width) * 100}%`,
    top: `${((box.y - padY) / page.height) * 100}%`,
    width: `${((box.w + padX * 2) / page.width) * 100}%`,
    height: `${((box.h + padY * 2) / page.height) * 100}%`,
  };
}

function Highlight({ box, page, on, active, soft }: { box: Box; page: StagePage; on: boolean; active: boolean; soft?: boolean }) {
  return (
    <div
      aria-hidden="true"
      style={place(box, page)}
      className={cn(
        "pointer-events-none absolute rounded-[3px] border transition-all duration-300",
        !on && "scale-95 opacity-0",
        on && !soft && "border-2 border-emerald-500 bg-emerald-400/15 opacity-100",
        on && soft && "border-transparent bg-emerald-400/10 opacity-100",
        on && active && "z-10 border-2 border-emerald-600 bg-emerald-400/35 shadow-[0_0_0_4px_rgb(16_185_129/0.25)]",
      )}
    />
  );
}

export function ScanStage({ pages, phase, looping, sweepMs, revealed, activeId }: Props) {
  return (
    <div
      className="relative overflow-hidden rounded-xl border border-border bg-white shadow-sm"
      style={{ ["--scan-ms" as string]: `${sweepMs}ms` }}
    >
      {pages.map((page, index) => (
        <div key={index} className={cn("relative", index > 0 && "border-t border-border")}>
          {page.iframeUrl ? (
            <iframe src={page.iframeUrl} title="Uploaded document" className="block h-[640px] w-full" />
          ) : (
            page.imageUrl && (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={page.imageUrl} alt={`Page ${index + 1} of the document being scanned`} draggable={false} className="block w-full select-none" />
            )
          )}

          {page.width > 0 &&
            Object.entries(page.rows).map(([rowIndex, box]) => (
              <Highlight
                key={`row:${rowIndex}`}
                box={box}
                page={page}
                on={revealed.has(`row:${rowIndex}`)}
                active={activeId === `row:${rowIndex}`}
                soft
              />
            ))}
        </div>
      ))}

      {phase === "scanning" && (
        <>
          {!looping && <div className="scan-trail" />}
          <div className={cn("scan-line", looping && "scan-line-loop")} />
        </>
      )}
    </div>
  );
}
