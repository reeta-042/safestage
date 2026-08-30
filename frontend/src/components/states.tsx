import type { ReactNode } from "react";
import { Loader2, AlertTriangle, Inbox } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-3 rounded-xl border border-border bg-card p-10 text-sm text-muted-foreground shadow-soft">
      <Loader2 className="size-4 animate-spin text-primary" />
      {label}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : "Something went wrong.";
  return (
    <Card className="border-destructive/30 shadow-soft">
      <CardContent className="flex flex-col items-start gap-3 p-6">
        <div className="flex items-center gap-2 text-destructive">
          <AlertTriangle className="size-4" />
          <span className="text-sm font-semibold">Request failed</span>
        </div>
        <p className="text-sm text-muted-foreground">{message}</p>
        {onRetry ? (
          <Button size="sm" variant="outline" onClick={onRetry}>
            Try again
          </Button>
        ) : null}
      </CardContent>
    </Card>
  );
}

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <Card className="shadow-soft">
      <CardContent className="flex flex-col items-center gap-3 p-10 text-center">
        <Inbox className="size-6 text-muted-foreground" />
        <p className="font-medium">{title}</p>
        {description ? <p className="max-w-md text-sm text-muted-foreground">{description}</p> : null}
        {action}
      </CardContent>
    </Card>
  );
}

export function UnsupportedNotice({ message }: { message?: string | null | undefined }) {
  return (
    <Card className="border-warning/40 bg-warning/5 shadow-soft">
      <CardContent className="p-5 text-sm text-foreground">
        {message || "This location or request is not supported by the backend."}
      </CardContent>
    </Card>
  );
}
