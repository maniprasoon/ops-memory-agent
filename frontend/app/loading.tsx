import { AgentLogo } from "@/components/brand";

export default function Loading() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#f4fbf8] px-5 text-[#10201d]">
      <div className="rounded-md border border-teal-900/10 bg-white p-5 shadow-sm">
        <AgentLogo />
        <p className="mt-4 text-sm text-teal-950/70">Preparing incident memory view...</p>
      </div>
    </main>
  );
}

