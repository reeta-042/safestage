import { cn } from "@/lib/utils";

function tone(level?: string | null) {
  const l = (level ?? "").toLowerCase();
  if (l.includes("extreme") || l.includes("severe") || l.includes("high") || l.includes("critical"))
    return "bg-danger/10 text-danger border-danger/30";
  if (l.includes("moderate") || l.includes("medium") || l.includes("caution"))
    return "bg-warning/10 text-warning border-warning/30";
  if (l.includes("low") || l.includes("safe") || l.includes("good"))
    return "bg-success/10 text-success border-success/30";
  return "bg-muted text-muted-foreground border-border";
}

export function RiskBadge({ level, className }: { level?: string | null | undefined; className?: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-medium capitalize",
        tone(level),
        className,
      )}
    >
      {level ?? "Unknown"}
    </span>
  );
}

export function ReadinessScore({
  score,
  label,
  size = "lg",
}: {
  score?: number | null;
  label?: string | null | undefined;
  size?: "sm" | "lg";
}) {
  const value = typeof score === "number" ? Math.max(0, Math.min(100, score)) : null;
  return (
    <div className="flex items-center gap-4">
      <div
        className={cn(
          "relative grid place-items-center rounded-full",
          size === "lg" ? "size-28" : "size-16",
        )}
        style={{
          background:
            value === null
              ? "var(--muted)"
              : `conic-gradient(var(--primary) ${value * 3.6}deg, var(--muted) 0deg)`,
        }}
      >
        <div
          className={cn(
            "grid place-items-center rounded-full bg-card",
            size === "lg" ? "size-22 p-5" : "size-12",
          )}
        >
          <span className={cn("font-semibold tabular-nums", size === "lg" ? "text-2xl" : "text-sm")}>
            {value === null ? "—" : value}
          </span>
        </div>
      </div>
      <div>
        <p className="text-xs uppercase tracking-wide text-muted-foreground">Readiness score</p>
        <p className={cn("font-semibold", size === "lg" ? "text-lg" : "text-sm")}>{label ?? "Not analyzed"}</p>
      </div>
    </div>
  );
}
