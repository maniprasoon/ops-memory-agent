import Link from "next/link";
import { GitBranch, MessageSquarePlus } from "lucide-react";

import { AppNav } from "@/components/brand";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const events = [
  {
    date: "Apr 18",
    title: "Postgres connection pool exhaustion on api-prod-3",
    category: "Database",
    cluster: "Connection pressure",
    score: 96
  },
  {
    date: "Apr 18",
    title: "DynamoDB hot partition throttled session writes",
    category: "Database",
    cluster: "Connection pressure",
    score: 88
  },
  {
    date: "Apr 18",
    title: "Regional packet loss between api-gateway and billing-service",
    category: "Networking",
    cluster: "Timeout path",
    score: 84
  },
  {
    date: "Apr 18",
    title: "Node heap leak in websocket-presence-service",
    category: "Memory leak",
    cluster: "Resource pressure",
    score: 79
  },
  {
    date: "Apr 18",
    title: "Stripe API elevated 500s delayed subscription renewals",
    category: "Third-party",
    cluster: "Provider failure",
    score: 75
  },
  {
    date: "Apr 18",
    title: "JWKS cache missed key rotation for auth-service",
    category: "Auth",
    cluster: "Identity edge",
    score: 73
  }
];

const clusters = [
  { name: "Connection pressure", color: "bg-amber-500", x: "left-[18%]", y: "top-[34%]" },
  { name: "Timeout path", color: "bg-teal-600", x: "left-[48%]", y: "top-[24%]" },
  { name: "Resource pressure", color: "bg-rose-500", x: "left-[64%]", y: "top-[58%]" },
  { name: "Provider failure", color: "bg-sky-600", x: "left-[32%]", y: "top-[68%]" },
  { name: "Identity edge", color: "bg-slate-700", x: "left-[78%]", y: "top-[36%]" }
];

export default function TimelinePage() {
  return (
    <main className="min-h-screen bg-[#f4fbf8] text-[#10201d]">
      <AppNav active="timeline" />
      <section className="mx-auto grid w-full max-w-7xl gap-6 px-5 py-6 lg:grid-cols-[1fr_430px]">
        <div className="space-y-5">
          <header className="rounded-md border border-teal-900/10 bg-white p-5 sm:flex sm:items-end sm:justify-between">
            <div>
              <p className="text-sm font-semibold uppercase tracking-normal text-teal-700">Learning Timeline</p>
              <h1 className="mt-2 text-3xl font-semibold tracking-normal">The agent learns from every incident.</h1>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-teal-950/70">
                Similar incidents cluster together as the memory bank grows, making the next outage faster to explain.
              </p>
            </div>
            <Button asChild>
              <Link href="/chat">
                <MessageSquarePlus className="mr-2 h-4 w-4" />
                New Incident
              </Link>
            </Button>
          </header>

          <div className="relative space-y-4 border-l-2 border-teal-700/30 pl-5">
            {events.map((event) => (
              <Card key={event.title} className="relative border-teal-900/10 bg-white shadow-sm">
                <span className="absolute -left-[30px] top-5 h-3 w-3 rounded-full bg-teal-700" />
                <CardHeader>
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <CardDescription>{event.date}</CardDescription>
                      <CardTitle className="mt-2">{event.title}</CardTitle>
                    </div>
                    <Badge variant="amber">{event.score}% similar</Badge>
                  </div>
                </CardHeader>
                <CardContent className="flex flex-wrap gap-2">
                  <Badge variant="slate">{event.category}</Badge>
                  <Badge variant="outline">{event.cluster}</Badge>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        <aside className="space-y-5">
          <Card className="border-teal-900/10 bg-white shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <GitBranch className="h-5 w-5 text-teal-700" />
                Similarity Clusters
              </CardTitle>
              <CardDescription>Incidents group around patterns the agent can reuse.</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="relative h-[420px] rounded-md border border-teal-900/10 bg-[#eef8f4]">
                <div className="absolute left-[18%] top-[34%] h-px w-[31%] rotate-[-10deg] bg-slate-300" />
                <div className="absolute left-[50%] top-[31%] h-px w-[20%] rotate-[48deg] bg-slate-300" />
                <div className="absolute left-[35%] top-[66%] h-px w-[28%] rotate-[-12deg] bg-slate-300" />
                {clusters.map((cluster) => (
                  <div key={cluster.name} className={`absolute ${cluster.x} ${cluster.y}`}>
                    <div className={`h-10 w-10 rounded-full ${cluster.color} shadow-sm`} />
                    <p className="mt-2 w-32 text-xs font-medium leading-4">{cluster.name}</p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
          <Card className="border-amber-300 bg-amber-100 shadow-sm">
            <CardHeader>
              <CardTitle>Memory signal</CardTitle>
              <CardDescription className="text-amber-900">
                Similarity scores rise as incidents share services, error signatures, and resolution steps.
              </CardDescription>
            </CardHeader>
          </Card>
        </aside>
      </section>
    </main>
  );
}
