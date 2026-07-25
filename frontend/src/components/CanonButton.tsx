"use client";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * The three button variants — DESIGN.md §6.1. There are no others.
 *
 * Built on the shadcn Button primitive, fully restyled. shadcn's own size
 * classes are overridden (`h-auto`) because the spec fixes padding at
 * 14px/28px rather than a fixed height.
 *
 * The signature detail: a primary button is always `label · gap-3 · →`, and on
 * hover ONLY the arrow moves (+3px on X). This repeats on every forward action
 * in the app and is the product's tactile signature.
 *
 * NEVER add glow, gradient, scale-on-hover, or box-shadow to a button.
 */
export function CanonButton({
  variant = "primary",
  arrow,
  className,
  children,
  ...props
  // `variant` is omitted from the base props so CANON's three variants replace
  // shadcn's set entirely, rather than intersecting with it.
}: Omit<React.ComponentProps<typeof Button>, "variant"> & {
  variant?: "primary" | "secondary" | "ghost";
  /** Show the `→` glyph. Defaults on for primary, off for the others. */
  arrow?: boolean;
}) {
  const showArrow = arrow ?? variant === "primary";

  const variants = {
    primary: cn(
      "bg-accent text-shell-void hover:bg-accent-dim",
      "hover:-translate-y-px active:translate-y-0 active:bg-accent-dim",
    ),
    secondary: cn(
      "border border-ink-line bg-transparent text-ink-bright",
      "hover:border-ink-muted hover:bg-shell-raised active:bg-shell-sunken",
    ),
    ghost: "border-transparent bg-transparent text-ink-muted hover:text-ink-bright",
  } as const;

  return (
    <Button
      className={cn(
        "type-label h-auto rounded-[2px] transition-all duration-[160ms] ease-out",
        variant === "ghost" ? "px-4 py-2.5" : "px-7 py-3.5",
        variants[variant],
        "disabled:pointer-events-none disabled:opacity-40",
        className,
      )}
      {...props}
    >
      {children}
      {showArrow ? (
        <span
          aria-hidden="true"
          className="ml-3 inline-block transition-transform duration-[160ms] ease-out group-hover/button:translate-x-[3px]"
        >
          →
        </span>
      ) : null}
    </Button>
  );
}
