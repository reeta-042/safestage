import { useEffect, useMemo, useRef, useState } from "react";
import { createFileRoute, useSearch } from "@tanstack/react-router";
import { useMutation } from "@tanstack/react-query";
import { Copy, FileText, Send, Sparkles, Trash2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { EventSelect } from "@/components/EventSelect";
import { ErrorState } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { api, type ChatMessage, type ChatResponse } from "@/lib/api";
import { useSelectedEvent } from "@/lib/useSelectedEvent";
import { cn } from "@/lib/utils";

const promptSuggestions = [
  "What cooling is needed?",
  "How should we adjust schedule for peak heat?",
  "Where are the highest risk sectors?",
  "What hydration plan do you recommend?",
];

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function renderInlineMarkdown(text: string): string {
  let value = escapeHtml(text)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>')
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/_([^_]+)_/g, "<em>$1</em>");

  return value;
}

function renderMarkdownContent(content: string): string {
  const lines = content.split(/\n/);
  const output: string[] = [];
  let paragraphBuffer: string[] = [];
  let listBuffer: string[] = [];
  let quoteBuffer: string[] = [];
  let inCodeBlock = false;
  let codeBuffer: string[] = [];

  const flushParagraph = () => {
    if (!paragraphBuffer.length) return;
    output.push(`<p>${renderInlineMarkdown(paragraphBuffer.join(" "))}</p>`);
    paragraphBuffer = [];
  };

  const flushList = () => {
    if (!listBuffer.length) return;
    output.push(`<ul>${listBuffer.map((entry) => `<li>${renderInlineMarkdown(entry)}</li>`).join("")}</ul>`);
    listBuffer = [];
  };

  const flushQuote = () => {
    if (!quoteBuffer.length) return;
    output.push(`<blockquote>${quoteBuffer.map((entry) => `<div>${renderInlineMarkdown(entry)}</div>`).join("")}</blockquote>`);
    quoteBuffer = [];
  };

  const flushCode = () => {
    if (!codeBuffer.length) return;
    output.push(`<pre><code>${escapeHtml(codeBuffer.join("\n"))}</code></pre>`);
    codeBuffer = [];
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();

    if (line.startsWith("```")) {
      flushParagraph();
      flushList();
      flushQuote();
      if (inCodeBlock) {
        flushCode();
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeBuffer.push(rawLine);
      continue;
    }

    if (!line.trim()) {
      flushParagraph();
      flushList();
      flushQuote();
      continue;
    }

    if (/^#{1,6}\s+/.test(line)) {
      flushParagraph();
      flushList();
      flushQuote();
      const level = line.match(/^#+/)?.[0].length ?? 1;
      output.push(`<h${level}>${renderInlineMarkdown(line.replace(/^#{1,6}\s+/, ""))}</h${level}>`);
      continue;
    }

    if (/^>\s+/.test(line)) {
      flushParagraph();
      flushList();
      quoteBuffer.push(line.replace(/^>\s+/, ""));
      continue;
    }

    if (/^[-*]\s+/.test(line)) {
      flushParagraph();
      flushQuote();
      listBuffer.push(line.replace(/^[-*]\s+/, ""));
      continue;
    }

    if (/^\|.*\|$/.test(line)) {
      flushParagraph();
      flushList();
      flushQuote();
      const current = [line];
      const nextRows: string[] = [];
      for (const next of lines.slice(lines.indexOf(rawLine) + 1)) {
        if (/^\|.*\|$/.test(next.trim())) {
          nextRows.push(next.trim());
        } else {
          break;
        }
      }
      const rows = [...current, ...nextRows];
      const cells = rows.map((row) => row.split("|").slice(1, -1).map((cell) => cell.trim()));
      const header = cells[0];
      const body = cells.slice(1);
      const tableRows = [
        `<thead><tr>${header.map((cell) => `<th>${renderInlineMarkdown(cell)}</th>`).join("")}</tr></thead>`,
        `<tbody>${body.map((row) => `<tr>${row.map((cell) => `<td>${renderInlineMarkdown(cell)}</td>`).join("")}</tr>`).join("")}</tbody>`,
      ];
      output.push(`<table class="markdown-table">${tableRows.join("")}</table>`);
      break;
    }

    paragraphBuffer.push(line);
  }

  flushParagraph();
  flushList();
  flushQuote();
  flushCode();

  return output.join("");
}

export const Route = createFileRoute("/assistant")({
  validateSearch: (search: Record<string, unknown>) => ({
    event_id: typeof search["event_id"] === "string" ? (search["event_id"] as string) : undefined,
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
  const [selectedAssistant, setSelectedAssistant] = useState<string | null>(null);
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

  const exportConsultation = () => {
    const blob = new Blob([JSON.stringify(history, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "safestage-consultation.json";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const assistantReply = useMemo(
    () => history.filter((entry) => entry.role === "assistant").at(-1)?.content ?? "",
    [history],
  );

  return (
    <AppShell>
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">AI planning assistant</h1>
          <p className="text-sm text-muted-foreground">Grounded event operations guidance for heat safety and scheduling.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setHistory([])} disabled={!history.length}>
            <Trash2 className="size-3.5" /> Clear
          </Button>
          <Button variant="outline" size="sm" onClick={exportConsultation} disabled={!history.length}>
            <FileText className="size-3.5" /> Export
          </Button>
        </div>
      </div>

      <div className="mt-6">
        <EventSelect value={activeId} onChange={select} />
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {promptSuggestions.map((prompt) => (
          <Button
            key={prompt}
            variant="secondary"
            size="sm"
            className="rounded-full"
            onClick={() => setInput(prompt)}
            disabled={!activeId}
          >
            {prompt}
          </Button>
        ))}
      </div>

      <Card className="mt-6 shadow-soft">
        <CardContent className="p-0">
          <div className="max-h-[58vh] min-h-[22rem] space-y-4 overflow-y-auto p-4 sm:p-5">
            {history.length === 0 ? (
              <div className="flex min-h-[18rem] items-center justify-center">
                <div className="max-w-md text-center text-sm text-muted-foreground">
                  <Sparkles className="mx-auto mb-3 size-5 text-primary" />
                  {activeId
                    ? "Ask about heat risk, scheduling, hydration, or crowd safety for this event."
                    : "Select an event to start the conversation."}
                </div>
              </div>
            ) : (
              history.map((message, index) => (
                <div key={`${message.role}-${index}`} className={cn("flex", message.role === "user" ? "justify-end" : "justify-start")}>
                  <div className={cn("max-w-[85%] rounded-2xl border px-4 py-3 text-sm shadow-sm", message.role === "user" ? "border-primary/20 bg-primary text-primary-foreground" : "border-border bg-muted text-foreground")}>
                    {message.role === "assistant" ? (
                      <div className="space-y-2">
                        <div className="flex items-center justify-end">
                          <button
                            type="button"
                            className="inline-flex items-center gap-1 text-[11px] text-muted-foreground underline-offset-2 hover:underline"
                            onClick={() => navigator.clipboard.writeText(message.content)}
                          >
                            <Copy className="size-3" /> Copy
                          </button>
                        </div>
                        <div className="markdown-wrap" dangerouslySetInnerHTML={{ __html: renderMarkdownContent(message.content) }} />
                        {selectedAssistant === message.content ? null : null}
                      </div>
                    ) : (
                      <div className="whitespace-pre-wrap">{message.content}</div>
                    )}
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

      {assistantReply ? (
        <div className="mt-4 flex justify-end">
          <Button variant="outline" size="sm" onClick={() => navigator.clipboard.writeText(assistantReply)}>
            Copy latest reply
          </Button>
        </div>
      ) : null}
    </AppShell>
  );
}

export default AssistantPage;

