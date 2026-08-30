import { Link } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { api, API_BASE_URL } from "@/lib/api";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/events/new", label: "Create Event" },
  { to: "/analysis", label: "Analysis" },
  { to: "/heatmap", label: "Heat Map" },
  { to: "/assistant", label: "AI Assistant" },
  { to: "/simulate", label: "What-If" },
] as const;

function BackendStatus() {
  const { isPending, isError } = useQuery({
    queryKey: ["health"],
    queryFn: api.health,
    retry: false,
    refetchInterval: 60_000,
  });
  const state = isPending ? "checking" : isError ? "offline" : "online";
  return (
    <span
      title={API_BASE_URL}
      className="inline-flex items-center gap-2 rounded-full border border-border bg-card px-3 py-1 text-xs text-muted-foreground"
    >
      <span
        className={cn(
          "size-2 rounded-full",
          state === "online" && "bg-success",
          state === "offline" && "bg-danger",
          state === "checking" && "bg-warning",
        )}
      />
      Backend {state}
    </span>
  );
}

export function Logo() {
  return (
    <Link to="/" className="flex items-center gap-2">
      <span className="grid size-8 place-items-center rounded-xl bg-brand-gradient text-sm font-bold text-primary-foreground">
        S
      </span>
      <span className="text-lg font-semibold tracking-tight">SafeStage</span>
    </Link>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-30 border-b border-border bg-background/85 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-3 px-4 py-3 sm:px-6">
          <Logo />
          <nav className="order-3 -mx-1 flex w-full gap-1 overflow-x-auto md:order-2 md:mx-0 md:w-auto">
            {NAV.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                activeProps={{ className: "bg-accent text-accent-foreground" }}
                className="whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
              >
                {item.label}
              </Link>
            ))}
          </nav>
          <div className="order-2 ml-auto md:order-3">
            <BackendStatus />
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6">{children}</main>
      <footer className="border-t border-border py-6 text-center text-xs text-muted-foreground">
        SafeStage — Plan safer. Decide smarter.
      </footer>
    </div>
  );
}
