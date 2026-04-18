import Link from "next/link";
import { ArrowRight, BrainCircuit } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

export function AgentLogo({ className }: { className?: string }) {
  return (
    <Link href="/" className={cn("inline-flex items-center gap-3", className)}>
      <div className="relative grid h-11 w-11 place-items-center rounded-md border border-teal-900 bg-teal-800 text-white shadow-sm">
        <div className="absolute left-2 top-2 h-2 w-2 rounded-sm bg-amber-300" />
        <div className="absolute bottom-2 right-2 h-2 w-2 rounded-sm bg-rose-300" />
        <BrainCircuit className="h-6 w-6" />
      </div>
      <div className="leading-tight">
        <p className="text-base font-semibold tracking-normal">Ops Memory Agent</p>
        <p className="text-xs font-medium text-teal-700">Incident recall system</p>
      </div>
    </Link>
  );
}

export function AppNav({ active }: { active?: "dashboard" | "chat" | "timeline" }) {
  const items = [
    { href: "/dashboard", label: "Dashboard", id: "dashboard" },
    { href: "/chat", label: "Agent", id: "chat" },
    { href: "/timeline", label: "Timeline", id: "timeline" }
  ] as const;

  return (
    <header className="border-b border-teal-900/10 bg-white/90 px-5 py-4 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <AgentLogo />
        <nav className="flex flex-wrap items-center gap-2">
          {items.map((item) => (
            <Button
              key={item.href}
              asChild
              variant={active === item.id ? "default" : "outline"}
              className={active === item.id ? "" : "border-teal-900/20 bg-white"}
            >
              <Link href={item.href}>{item.label}</Link>
            </Button>
          ))}
        </nav>
      </div>
    </header>
  );
}

export function LaunchAgentButton({ className }: { className?: string }) {
  return (
    <Button asChild className={className}>
      <Link href="/dashboard">
        Go to agent
        <ArrowRight className="ml-2 h-4 w-4" />
      </Link>
    </Button>
  );
}

