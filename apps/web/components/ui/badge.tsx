import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none",
  {
    variants: {
      variant: {
        default: "border-transparent bg-primary text-primary-foreground",
        secondary: "border-transparent bg-secondary text-secondary-foreground",
        outline: "border-input text-foreground",
        // Reserved for a genuinely adverse outcome the user must register as such (e.g. a
        // rejected loan application) — distinct from the confidence-tier badges below,
        // which deliberately avoid red because low confidence just means uncertain data.
        destructive: "border-transparent bg-destructive text-destructive-foreground",
        // Confidence-tier colours for the risk assessment report: green = high, amber =
        // medium, grey/muted = low or unavailable. Never red — low confidence means
        // uncertain data, not a bad applicant, and red would misread as an alarm.
        success:
          "border-transparent bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
        warning:
          "border-transparent bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
        muted: "border-transparent bg-muted text-muted-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
