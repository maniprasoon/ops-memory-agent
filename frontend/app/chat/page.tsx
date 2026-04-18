"use client";

import { FormEvent, useMemo, useState } from "react";
import Link from "next/link";
import { DatabaseZap, MessageSquarePlus, SendHorizonal } from "lucide-react";

import { AgentLogo } from "@/components/brand";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Textarea } from "@/components/ui/textarea";
import { parseMemories, type MemoryCard } from "@/lib/memory";

type Message = {
  role: "user" | "assistant";
  content: string;
};

type ChatPayload = {
  response?: string;
  detail?: string;
  memories_recalled?: string[];
};

function newSessionId() {
  return `incident-${Date.now().toString(36)}`;
}

export default function ChatPage() {
  const [sessionId, setSessionId] = useState(newSessionId);
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [memoryCards, setMemoryCards] = useState<MemoryCard[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const canSend = useMemo(
    () => message.trim().length > 0 && sessionId.trim().length > 0,
    [message, sessionId]
  );

  function startNewIncident() {
    setSessionId(newSessionId());
    setMessage("");
    setMessages([]);
    setMemoryCards([]);
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSend || isLoading) return;

    const nextMessage = message.trim();
    setMessages((current) => [...current, { role: "user", content: nextMessage }]);
    setMessage("");
    setIsLoading(true);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId.trim(), message: nextMessage })
      });
      const data = (await response.json()) as ChatPayload;
      if (!response.ok) {
        throw new Error(data.detail ?? "Chat request failed");
      }
      const recalled = parseMemories(data.memories_recalled ?? []);
      setMemoryCards(recalled);
      setMessages((current) => [...current, { role: "assistant", content: data.response ?? "" }]);
    } catch (error) {
      const content = error instanceof Error ? error.message : "Something went wrong";
      setMessages((current) => [...current, { role: "assistant", content }]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-[#f4fbf8] text-[#10201d]">
      <section className="grid min-h-screen grid-rows-[auto_1fr]">
        <header className="flex flex-col gap-4 border-b border-teal-900/10 bg-white px-5 py-4 lg:flex-row lg:items-center lg:justify-between">
          <AgentLogo />
          <div className="flex flex-wrap items-center gap-3">
            <Badge variant="slate">Session {sessionId}</Badge>
            <Button variant="secondary" onClick={startNewIncident}>
              <MessageSquarePlus className="mr-2 h-4 w-4" />
              New Incident
            </Button>
            <Button asChild variant="outline" className="border-teal-900/20 bg-white">
              <Link href="/dashboard">Dashboard</Link>
            </Button>
          </div>
        </header>

        <div className="grid min-h-0 gap-0 lg:grid-cols-[minmax(0,1fr)_450px]">
          <section className="flex min-h-0 flex-col border-r border-teal-900/10 bg-white">
            <ScrollArea className="min-h-0 flex-1 px-5 py-5">
              {messages.length === 0 ? (
                <div className="mx-auto flex min-h-[520px] max-w-2xl flex-col items-center justify-center text-center">
                  <Badge variant="amber">Memory panel is live</Badge>
                  <h1 className="mt-4 text-3xl font-semibold tracking-normal">Ask a production alert.</h1>
                  <p className="mt-3 text-sm leading-6 text-teal-950/70">
                    The agent searches past incidents first. Recalled memories appear on the right before the
                    recommendation lands in chat.
                  </p>
                </div>
              ) : (
                <div className="mx-auto max-w-3xl space-y-4">
                  {messages.map((item, index) => (
                    <article
                      key={`${item.role}-${index}`}
                      className={item.role === "user" ? "ml-auto max-w-[82%]" : "mr-auto max-w-[82%]"}
                    >
                      <div
                        className={
                          item.role === "user"
                            ? "rounded-md bg-teal-700 px-4 py-3 text-sm leading-6 text-white"
                            : "rounded-md border border-slate-200 bg-slate-100 px-4 py-3 text-sm leading-6 text-slate-900"
                        }
                      >
                        {item.content}
                      </div>
                    </article>
                  ))}
                  {isLoading ? <p className="text-sm text-teal-700">Searching memory before responding...</p> : null}
                </div>
              )}
            </ScrollArea>

            <form className="border-t border-teal-900/10 bg-[#eef8f4] p-5" onSubmit={onSubmit}>
              <div className="mx-auto flex max-w-3xl flex-col gap-3">
                <Textarea
                  className="border-teal-900/20 bg-white text-slate-950 placeholder:text-slate-500"
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="Production alert: API timeout spike. What have we seen before?"
                />
                <div className="flex justify-end">
                  <Button type="submit" disabled={!canSend || isLoading}>
                    <SendHorizonal className="mr-2 h-4 w-4" />
                    Send
                  </Button>
                </div>
              </div>
            </form>
          </section>

          <aside className="min-h-0 bg-amber-50 text-slate-950">
            <div className="flex h-full min-h-0 flex-col">
              <div className="border-b border-amber-300 bg-amber-100 px-5 py-4">
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold uppercase tracking-normal text-amber-900">Memory Retrieved</p>
                    <h2 className="mt-1 text-xl font-semibold tracking-normal">Hindsight context</h2>
                  </div>
                  <DatabaseZap className="h-7 w-7 text-amber-800" />
                </div>
              </div>
              <ScrollArea className="min-h-0 flex-1 p-5">
                <div className="space-y-4">
                  {memoryCards.length === 0 ? (
                    <Card className="border-dashed border-amber-300 bg-white">
                      <CardHeader>
                        <CardTitle>No memories retrieved yet</CardTitle>
                        <CardDescription>Ask about an incident and this panel becomes the proof trail.</CardDescription>
                      </CardHeader>
                    </Card>
                  ) : (
                    memoryCards.map((memory) => (
                      <Card key={memory.id} className="border-amber-300 bg-amber-100 shadow-sm ring-1 ring-amber-300/60">
                        <CardHeader>
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <CardTitle>From memory: {memory.title}</CardTitle>
                              <CardDescription className="mt-2 text-amber-900">{memory.date}</CardDescription>
                            </div>
                            <Badge variant="amber">{memory.score}% similar</Badge>
                          </div>
                        </CardHeader>
                        <CardContent>
                          <Badge variant="outline" className="mb-3 bg-white text-amber-950">
                            This informed the response
                          </Badge>
                          <p className="text-sm leading-6 text-amber-950">{memory.body}</p>
                        </CardContent>
                      </Card>
                    ))
                  )}
                </div>
              </ScrollArea>
            </div>
          </aside>
        </div>
      </section>
    </main>
  );
}
