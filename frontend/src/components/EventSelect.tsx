import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { api, type EventRecord } from "@/lib/api";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export function useEventsQuery() {
  return useQuery<EventRecord[]>({ queryKey: ["events"], queryFn: api.listEvents, retry: false });
}

export function EventSelect({
  value,
  onChange,
  label = "Event",
}: {
  value: string;
  onChange: (id: string) => void;
  label?: string;
}) {
  const { data, isPending, isError, error } = useEventsQuery();

  return (
    <div className="grid gap-2 sm:max-w-md">
      <Label>{label}</Label>
      <Select value={value} onValueChange={onChange} disabled={isPending || isError || !data?.length}>
        <SelectTrigger className="bg-card">
          <SelectValue placeholder={isPending ? "Loading events…" : "Select an event"} />
        </SelectTrigger>
        <SelectContent>
          {(data ?? []).map((ev) => (
            <SelectItem key={ev.id} value={ev.id}>
              {ev.name} — {ev.venue_name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {isError ? (
        <p className="text-xs text-destructive">
          {error instanceof Error ? error.message : "Could not load events."}
        </p>
      ) : null}
      {!isPending && !isError && !data?.length ? (
        <p className="text-xs text-muted-foreground">
          No events yet.{" "}
          <Link to="/events/new" className="text-primary underline">
            Create one
          </Link>
          .
        </p>
      ) : null}
    </div>
  );
}
