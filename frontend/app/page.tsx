import Link from "next/link";
import { ArrowRight, CheckCircle2, Cpu, Database, Network, ServerCog } from "lucide-react";

import { AgentLogo, LaunchAgentButton } from "@/components/brand";
import { LandingOpsVisual } from "@/components/ops-visual";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const stack = [
  { label: "Next.js 14", detail: "App Router frontend with Tailwind and shadcn/ui" },
  { label: "FastAPI", detail: "Async Python backend with `/api/chat` and memory endpoints" },
  { label: "Hindsight", detail: "Durable incident memory for save and recall" },
  { label: "LangChain + Groq", detail: "ReAct incident agent using qwen/qwen3-32b" }
];

const examples = [
  "Production alert: API timeout spike. What have we seen before?",
  "Database connection error after orders-service deploy",
  "Log this as P1: checkout requests timing out in us-east-1"
];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-[#f4fbf8] text-[#10201d]">
      <header className="border-b border-teal-900/10 bg-white/90 px-5 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <AgentLogo />
          <nav className="flex flex-wrap gap-2">
            <Button asChild variant="outline" className="border-teal-900/20 bg-white">
              <Link href="/timeline">Timeline</Link>
            </Button>
            <LaunchAgentButton />
          </nav>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl gap-8 px-5 py-10 lg:grid-cols-[1.05fr_0.95fr] lg:items-center">
        <div>
          <Badge variant="amber">Memory-first incident response</Badge>
          <h1 className="mt-5 max-w-3xl text-5xl font-semibold leading-tight tracking-normal">
            The agent that remembers how production broke last time.
          </h1>
          <p className="mt-5 max-w-2xl text-lg leading-8 text-teal-950/75">
            Ops Memory Agent connects a LangChain incident agent to Hindsight so every answer can cite
            past outages, exact fixes, root causes, and runbook patterns.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <LaunchAgentButton />
            <Button asChild variant="outline" className="border-teal-900/20 bg-white">
              <Link href="/chat">
                Open chat
                <ArrowRight className="ml-2 h-4 w-4" />
              </Link>
            </Button>
          </div>
        </div>

        <div className="overflow-hidden rounded-md border border-teal-900/10 bg-white p-3 shadow-sm">
          <LandingOpsVisual />
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-5 px-5 pb-10 lg:grid-cols-4">
        {stack.map((item, index) => {
          const Icon = [Cpu, ServerCog, Database, Network][index];
          return (
            <Card key={item.label} className="border-teal-900/10 bg-white">
              <CardHeader>
                <Icon className="h-6 w-6 text-teal-700" />
                <CardTitle>{item.label}</CardTitle>
                <CardDescription>{item.detail}</CardDescription>
              </CardHeader>
            </Card>
          );
        })}
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-5 pb-12 lg:grid-cols-[0.9fr_1.1fr]">
        <Card className="border-teal-900/10 bg-white">
          <CardHeader>
            <CardTitle>How to test the demo</CardTitle>
            <CardDescription>Seed memory, start the backend, start the frontend, then ask a real alert.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3 text-sm leading-6">
            {[
              "1. Install Python dependencies: `pip install -r requirements.txt` from the repo root.",
              "2. Start backend: run `py -m uvicorn app.main:app --reload --port 8000` from `/backend`.",
              "3. Start frontend & Seed memory automatically: run `npm install` then `npm run dev` from `/frontend`.",
              "4. Start testing: Open `/chat` and try one of the example prompts!"
            ].map((step) => (
              <div key={step} className="flex gap-3 rounded-md bg-[#eef8f4] p-3">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-teal-700" />
                <span>{step}</span>
              </div>
            ))}
          </CardContent>
        </Card>

        <Card className="border-amber-300 bg-amber-100">
          <CardHeader>
            <CardTitle>Prompts that prove memory is working</CardTitle>
            <CardDescription className="text-amber-900">
              The right panel in chat should fill with amber memory cards after each response.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {examples.map((example) => (
              <div key={example} className="rounded-md border border-amber-300 bg-white p-3 text-sm">
                {example}
              </div>
            ))}
          </CardContent>
        </Card>
      </section>
    </main>
  );
}
