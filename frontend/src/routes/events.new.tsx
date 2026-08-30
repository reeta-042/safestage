import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { AppShell } from "@/components/AppShell";
import { ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, type EventCreate, type EventRecord } from "@/lib/api";
import { setStoredEventId } from "@/lib/useSelectedEvent";

export const Route = createFileRoute("/events/new")({
  head: () => ({
    meta: [
      { title: "Create Event — SafeStage" },
      { name: "description", content: "Add an outdoor event with venue, coordinates, attendance and schedule." },
      { property: "og:title", content: "Create Event — SafeStage" },
      { property: "og:description", content: "Add an outdoor event to analyze its climate readiness." },
    ],
  }),
  component: CreateEvent,
});

interface FormState {
  name: string;
  event_type: string;
  venue_name: string;
  address: string;
  latitude: string;
  longitude: string;
  attendance: string;
  start_datetime: string;
  end_datetime: string;
  user_id: string;
}

const INITIAL: FormState = {
  name: "",
  event_type: "",
  venue_name: "",
  address: "",
  latitude: "",
  longitude: "",
  attendance: "",
  start_datetime: "",
  end_datetime: "",
  user_id: "",
};

function CreateEvent() {
  const [form, setForm] = useState<FormState>(INITIAL);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const mutation = useMutation<EventRecord, unknown, EventCreate>({
    mutationFn: api.createEvent,
    onSuccess: (event) => {
      setStoredEventId(event.id);
      void queryClient.invalidateQueries({ queryKey: ["events"] });
      toast.success("Event created");
      void navigate({ to: "/analysis", search: { event_id: event.id } });
    },
  });

  const set = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }));

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate({
      name: form.name,
      event_type: form.event_type,
      venue_name: form.venue_name,
      address: form.address,
      latitude: Number(form.latitude),
      longitude: Number(form.longitude),
      attendance: Number(form.attendance),
      start_datetime: new Date(form.start_datetime).toISOString(),
      end_datetime: new Date(form.end_datetime).toISOString(),
      user_id: form.user_id.trim() === "" ? null : form.user_id.trim(),
    });
  };

  return (
    <AppShell>
      <h1 className="text-2xl font-semibold tracking-tight">Create event</h1>
      <p className="text-sm text-muted-foreground">
        These fields are sent to the SafeStage backend as <code>POST /events</code>.
      </p>

      <Card className="mt-6 max-w-3xl shadow-soft">
        <CardHeader>
          <CardTitle className="text-base">Event details</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="grid gap-5 sm:grid-cols-2" onSubmit={onSubmit}>
            <Field id="name" label="Event name" value={form.name} onChange={set("name")} required />
            <Field
              id="event_type"
              label="Event type"
              value={form.event_type}
              onChange={set("event_type")}
              placeholder="concert, festival, sports…"
              required
            />
            <Field id="venue_name" label="Venue name" value={form.venue_name} onChange={set("venue_name")} required />
            <Field id="address" label="Address" value={form.address} onChange={set("address")} required />
            <Field
              id="latitude"
              label="Latitude"
              type="number"
              step="any"
              value={form.latitude}
              onChange={set("latitude")}
              required
            />
            <Field
              id="longitude"
              label="Longitude"
              type="number"
              step="any"
              value={form.longitude}
              onChange={set("longitude")}
              required
            />
            <Field
              id="attendance"
              label="Attendance"
              type="number"
              min="0"
              value={form.attendance}
              onChange={set("attendance")}
              required
            />
            <Field
              id="user_id"
              label="User ID (optional)"
              value={form.user_id}
              onChange={set("user_id")}
              placeholder="leave blank for null"
            />
            <Field
              id="start_datetime"
              label="Start date & time"
              type="datetime-local"
              value={form.start_datetime}
              onChange={set("start_datetime")}
              required
            />
            <Field
              id="end_datetime"
              label="End date & time"
              type="datetime-local"
              value={form.end_datetime}
              onChange={set("end_datetime")}
              required
            />

            <div className="sm:col-span-2">
              {mutation.isError ? <ErrorState error={mutation.error} /> : null}
            </div>

            <div className="sm:col-span-2">
              <Button type="submit" disabled={mutation.isPending}>
                {mutation.isPending ? "Creating…" : "Create event"}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </AppShell>
  );
}

function Field({
  id,
  label,
  ...props
}: { id: string; label: string } & React.ComponentProps<typeof Input>) {
  return (
    <div className="grid gap-2">
      <Label htmlFor={id}>{label}</Label>
      <Input id={id} {...props} />
    </div>
  );
}
