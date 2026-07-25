import { cn } from "@/lib/utils";

/**
 * The Index Mark — DESIGN.md §1, signature move #2.
 *
 * A small monospace catalog number carried by every referenceable element
 * (`E03`, `F-127`, `CH-02`). This single detail is what makes the product feel
 * systematised rather than templated. Always `font-data`, always `--ink-faint`.
 */
export function IndexMark({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <span className={cn("type-index text-ink-faint", className)}>
      {children}
    </span>
  );
}
