import type { ReactNode } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

export function isEmptyValue(value: unknown): boolean {
  if (value === null || value === undefined || value === "") return true;
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === "object") return Object.keys(value as object).length === 0;
  return false;
}

function humanize(key: string) {
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function DataValue({ value, depth = 0 }: { value: unknown; depth?: number }) {
  if (isEmptyValue(value)) return <span className="text-muted-foreground">—</span>;

  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return <span className="whitespace-pre-wrap break-words">{String(value)}</span>;
  }

  if (Array.isArray(value)) {
    const primitives = value.every((v) => typeof v !== "object" || v === null);
    return (
      <ul className={cn("space-y-2", primitives && "list-disc pl-5 space-y-1")}>
        {value.map((item, i) => (
          <li key={i} className={cn(!primitives && "rounded-lg border border-border bg-muted/40 p-3")}>
            <DataValue value={item} depth={depth + 1} />
          </li>
        ))}
      </ul>
    );
  }

  const entries = Object.entries(value as Record<string, unknown>);
  return (
    <dl className="space-y-2">
      {entries.map(([k, v]) => (
        <div key={k} className="grid gap-1 sm:grid-cols-[minmax(120px,220px)_1fr] sm:gap-4">
          <dt className="text-xs font-medium uppercase tracking-wide text-muted-foreground">{humanize(k)}</dt>
          <dd className="text-sm">
            <DataValue value={v} depth={depth + 1} />
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function DataCard({
  title,
  value,
  children,
  className,
}: {
  title: string;
  value?: unknown;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <Card className={cn("shadow-soft", className)}>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">{title}</CardTitle>
      </CardHeader>
      <CardContent className="text-sm">{children ?? <DataValue value={value} />}</CardContent>
    </Card>
  );
}
