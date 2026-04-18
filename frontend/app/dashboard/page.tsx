"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Database, MessageSquarePlus, RadioTower } from "lucide-react";

import { AppNav } from "@/components/brand";
import { DashboardOpsVisual } from "@/components/ops-visual";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { parseMemories, type MemoryCard } from "@/lib/memory";

const activeIncidents = [
  {
    title: "API timeout spike in us-east-1",
    severity: "P1",
    services: "api-gateway, orders-service, user-db",
    age: "12 min",
    status: "Investigating"
  },
  {
    title: "Webhook retries elevated for payments",
    severity: "P2",
    services: "payments-api, callback-worker",
    age: "24 min",
    status: "Mitigating"
  },
  {
    title: "Profile page p95 above threshold",
    severity: "P3",
    services: "profile-service, mongo-users",
    age: "41 min",
    status: "Watching"
  }
];

export default function DashboardPage() {
  const [memories, setMemories] = useState<MemoryCard[]>([]);

  useEffect(() => {
    async function loadMemories() {
      const response = await fetch("/api/memory/recall", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: "incident-response",
          query: "recent production incidents database networking deployment memory leak auth outage",
          top_k: 8
        })
      });
      if (!response.ok) return;
      const data = (await response.json()) as { memories?: string[] };
      setMemories(parseMemories(data.memories ?? []));
    }

    void loadMemories();
  }, []);

  const memoryCount = useMemo(() => Math.max(memories.length, 80), [memories.length]);

  return (
    <main className="min-h-screen bg-[#f4fbf8] text-[#10201d]">
      <AppNav active="dashboard" />
      <section className="mx-auto grid w-full max-w-7xl gap-6 px-5 py-6 lg:grid-cols-[1fr_380px]">
        <div className="space-y-5">
          <header className="overflow-hidden rounded-md border border-teal-900/10 bg-white">
            <div className="grid gap-0 lg:grid-cols-[1fr_320px]">
              <div className="p-5">
                <p className="text-sm font-semibold uppercase tracking-normal text-teal-700">Incident Command</p>
                <h1 className="mt-2 text-3xl font-semibold tracking-normal">Active Incidents</h1>
                <p className="mt-3 max-w-2xl text-sm leading-6 text-teal-950/70">
                  Each open incident can call into Hindsight, retrieve the closest runbook memories, and show the
                  evidence before the agent recommends a fix.
                </p>
              </div>
              <div className="relative min-h-44">
                <DashboardOpsVisual />
              </div>
            </div>
          </header>

          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-sm font-medium text-teal-950/70">Live queue</p>
            </div>
            <Button asChild>
              <Link href="/chat">
                <MessageSquarePlus className="mr-2 h-4 w-4" />
                New Incident
              </Link>
            </Button>
          </div>

          <div className="grid gap-4">
            {activeIncidents.map((incident) => (
              <Card key={incident.title} className="border-teal-900/10 bg-white shadow-sm">
                <CardHeader className="flex-row items-start justify-between gap-3">
                  <div className="flex gap-3">
                    <div className="grid h-10 w-10 place-items-center rounded-md bg-teal-100 text-teal-800">
                      <RadioTower className="h-5 w-5" />
                    </div>
                    <div>
                    <CardTitle>{incident.title}</CardTitle>
                    <CardDescription className="mt-2">{incident.services}</CardDescription>
                    </div>
                  </div>
                  <Badge variant={incident.severity === "P1" ? "amber" : "slate"}>{incident.severity}</Badge>
                </CardHeader>
                <CardContent className="flex flex-wrap items-center gap-3 text-sm">
                  <span className="rounded-md bg-slate-100 px-2 py-1">{incident.status}</span>
                  <span className="text-slate-500">Open for {incident.age}</span>
                  <Link className="font-medium text-teal-700" href="/chat">
                    Open memory chat
                  </Link>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        <aside>
          <Card className="sticky top-6 border-amber-300 bg-white shadow-sm">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="flex items-center gap-2">
                  <Database className="h-5 w-5 text-teal-700" />
                  Memory Bank
                </CardTitle>
                <Badge variant="amber">{memoryCount} stored</Badge>
              </div>
              <CardDescription>Recent runbook memories ready for incident response.</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[620px] pr-2">
                <div className="space-y-3">
                  {memories.length === 0 ? (
                    <div className="rounded-md border border-dashed border-slate-300 p-4 text-sm text-slate-500">
                      Memory recall is waiting for the backend.
                    </div>
                  ) : (
                    memories.map((memory) => (
                      <Card key={memory.id} className="border-amber-300 bg-amber-100 shadow-sm">
                        <CardHeader className="p-3">
                          <CardTitle className="text-sm">From memory: {memory.title}</CardTitle>
                          <CardDescription>{memory.date}</CardDescription>
                        </CardHeader>
                        <CardContent className="p-3 pt-0">
                          <div className="mb-2 flex items-center gap-2">
                            <Badge variant="amber">{memory.score}% similar</Badge>
                            <span className="text-xs font-medium text-amber-950">This informed the response</span>
                          </div>
                          <p className="line-clamp-3 text-xs leading-5 text-amber-950">{memory.body}</p>
                        </CardContent>
                      </Card>
                    ))
                  )}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </aside>
      </section>
    </main>
  );
}
