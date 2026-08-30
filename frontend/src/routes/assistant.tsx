import { useEffect, useRef, useState } from "react";
import { createFileRoute, useSearch } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { Send } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { EventSelect } from "@/components/EventSelect";
import { ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { api, type ChatMessage, type ChatResponse } from "@/lib/api";
import { useSelectedEvent } from "@/lib/useSelectedEvent";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/assistant")({
  validateSearch: (search: Record<string, unknown>) => ({
    event_id: typeof search['event_id'] === "string" ? (search['event_id'] as string) : undefined,
  }),
  head: () => ({
    meta: [
      { title: "AI Planning Assistant — SafeStage" },
      { name: "description", content: "Chat with the SafeStage planning assistant about your event's climate safety." },
      { property: "og:title", content: "AI Planning Assistant — SafeStage" },
      { property: "og:description", content: "Ask grounded questions about your event's climate risk." },
    ],
  }),
  component: AssistantPage,
});

function AssistantPage() {
  const search = useSearch({ from: "/assistant" });
  const { eventId, select } = useSelectedEvent();
  const activeId = search.event_id ?? eventId;
  const [history, setHistory] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (search.event_id && search.event_id !== eventId) select(search.event_id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search.event_id]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [history]);

  const chat = useMutation<ChatResponse, unknown, { message: string; history: ChatMessage[] }>({
    mutationFn: ({ message, history: h }) => api.chat({ event_id: activeId, message, history: h }),
    onSuccess: (res) => {
      setHistory((prev) => [...prev, { role: "assistant", content: res.reply }]);
    },
  });

  const send = () => {
    const message = input.trim();
    if (!message || !activeId) return;
    const priorHistory = history;
    setHistory((prev) => [...prev, { role: "user", content: message }]);
    setInput("");
    chat.mutate({ message, history: priorHistory });
  };

  return (
    <AppShell>
      <h1 className="text-2xl font-semibold tracking-tight">AI planning assistant</h1>
      <p className="text-sm text-muted-foreground">
        Sends <code>POST /chat</code> with the full conversation history.
      </p>

      <div className="mt-6">
        <EventSelect value={activeId} onChange={select} />
      </div>

      <Card className="mt-6 shadow-soft">
        <CardContent className="p-0">
          <div className="max-h-[55vh] min-h-64 space-y-4 overflow-y-auto p-5">
            {history.length === 0 ? (
              <p className="py-10 text-center text-sm text-muted-foreground">
                {activeId
                  ? "Ask about heat risk, scheduling, hydration planning or crowd safety for this event."
                  : "Select an event to start the conversation."}
              </p>
            ) : (
              history.map((m, i) => (
                <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                  <div
                    className={cn(
                      "max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm",
                      m.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-foreground",
                    )}
                  >
                    {m.content}
                  </div>
                </div>
              ))
            )}
            {chat.isPending ? (
              <div className="flex justify-start">
                <div className="rounded-2xl bg-muted px-4 py-2.5 text-sm text-muted-foreground">Thinking…</div>
              </div>
            ) : null}
            <div ref={endRef} />
          </div>

          {chat.isError ? (
            <div className="px-5 pb-4">
              <ErrorState error={chat.error} />
            </div>
          ) : null}

          <div className="flex items-end gap-3 border-t border-border p-4">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  send();
                }
              }}
              placeholder={activeId ? "Ask the assistant…" : "Select an event first"}
              disabled={!activeId || chat.isPending}
              className="min-h-11 resize-none bg-card"
              rows={1}
            />
            <Button onClick={send} disabled={!activeId || !input.trim() || chat.isPending}>
              <Send className="size-4" /> Send
            </Button>
          </div>
        </CardContent>
      </Card>
    </AppShell>
  );
}
