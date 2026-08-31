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

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatChatText(content: string): string {
  const escaped = escapeHtml(content);
  const lines = escaped.split(/\n/).map((line) => line.trimEnd());

  return lines
    .map((line) => {
      const normalized = line.trim();
      if (!normalized) return "<br />";

      if (/^#{1,6}\s+/.test(normalized)) {
        return `<div class="font-semibold">${normalized.replace(/^#{1,6}\s+/, "")}</div>`;
      }

      if (/^[-*]\s+/.test(normalized)) {
        return `<div class="flex items-start gap-2"><span class="mt-1 text-xs">•</span><span>${normalized.replace(/^[-*]\s+/, "")}</span></div>`;
      }

      let formatted = normalized
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(/`([^`]+)`/g, "<code class=\"rounded bg-black/5 px-1 py-0.5 text-[0.8em]\">$1</code>")
        .replace(/\[(.+?)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer" class="underline underline-offset-2">$1</a>');

      return `<div>${formatted}</div>`;
    })
    .join("");
}

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
    mutationFn: async ({ message, history: h }: { message: string; history: ChatMessage[] }) =>
      api.chat({ event_id: activeId as string, message, history: h }),
    onSuccess: (res: ChatResponse) => {
      setHistory((prev: ChatMessage[]) => [...prev, { role: "assistant", content: res.reply }]);
    },
  });

  const send = () => {
    const message = input.trim();
    if (!message || !activeId) return;
    const priorHistory = history;
    setHistory((prev: ChatMessage[]) => [...prev, { role: "user", content: message }]);
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
          <div className="max-h-[55vh] min-h-[22rem] space-y-4 overflow-y-auto p-4 sm:p-5">
            {history.length === 0 ? (
              <div className="flex min-h-[18rem] items-center justify-center">
                <p className="max-w-md text-center text-sm text-muted-foreground">
                  {activeId
                    ? "Ask about heat risk, scheduling, hydration planning or crowd safety for this event."
                    : "Select an event to start the conversation."}
                </p>
              </div>
            ) : (
              history.map((m: ChatMessage, i: number) => (
                <div key={i} className={cn("flex", m.role === "user" ? "justify-end" : "justify-start")}>
                  <div
                    className={cn(
                      "max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm",
                      m.role === "user"
                        ? "bg-primary text-primary-foreground"
                        : "bg-muted text-foreground",
                    )}
                    dangerouslySetInnerHTML={
                      m.role === "assistant"
                        ? { __html: formatChatText(m.content) }
                        : undefined
                    }
                  >
                    {m.role === "user" ? m.content : null}
                  </div>
                </div>
              ))
            )}
            {chat.isPending ? (
              <div className="flex justify-start">
                <div className="rounded-2xl bg-muted px-4 py-3 text-sm text-muted-foreground">Thinking…</div>
              </div>
            ) : null}
            <div ref={endRef} />
          </div>

          {chat.isError ? (
            <div className="px-5 pb-4">
              <ErrorState error={chat.error} />
            </div>
          ) : null}

          <div className="flex flex-col gap-3 border-t border-border p-4 sm:flex-row sm:items-end">
            <Textarea
              value={input}
              onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setInput(e.target.value)}
              onKeyDown={(e: React.KeyboardEvent<HTMLTextAreaElement>) => {
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
            <Button onClick={send} disabled={!activeId || !input.trim() || chat.isPending} className="sm:self-end">
              <Send className="size-4" /> Send
            </Button>
          </div>
        </CardContent>
      </Card>
    </AppShell>
  );
}
