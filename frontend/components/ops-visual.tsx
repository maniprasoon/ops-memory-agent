import { Activity, Database, GitBranch, RadioTower } from "lucide-react";

export function LandingOpsVisual() {
  return (
    <div className="relative h-72 overflow-hidden rounded-md bg-[#112b26] p-4 text-white">
      <div className="grid h-full grid-cols-[1fr_0.82fr] gap-3">
        <div className="flex flex-col gap-3">
          <div className="rounded-md border border-teal-300/30 bg-teal-950/70 p-4">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold text-teal-100">Incident pulse</span>
              <Activity className="h-5 w-5 text-amber-300" />
            </div>
            <div className="mt-5 grid grid-cols-12 items-end gap-1">
              {[24, 42, 35, 61, 48, 74, 52, 88, 64, 76, 50, 68].map((height, index) => (
                <div key={index} className="rounded-sm bg-amber-300" style={{ height }} />
              ))}
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            {[
              ["30", "memories"],
              ["7", "checks"],
              ["4", "tools"]
            ].map(([value, label]) => (
              <div key={label} className="rounded-md bg-white/10 p-3">
                <p className="text-2xl font-semibold">{value}</p>
                <p className="text-xs text-teal-100">{label}</p>
              </div>
            ))}
          </div>
        </div>
        <div className="rounded-md border border-amber-300/40 bg-amber-100 p-4 text-amber-950">
          <p className="text-sm font-semibold">Memory retrieved</p>
          <div className="mt-4 space-y-3">
            {["Postgres pool exhaustion", "Packet loss path", "JWKS cache miss"].map((item, index) => (
              <div key={item} className="rounded-md border border-amber-300 bg-white p-3">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold">{item}</span>
                  <span className="rounded-md bg-amber-100 px-2 py-0.5 text-xs">{96 - index * 7}%</span>
                </div>
                <div className="mt-3 h-2 rounded-sm bg-amber-200" />
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export function DashboardOpsVisual() {
  return (
    <div className="h-full min-h-44 bg-[#112b26] p-4 text-white">
      <div className="grid h-full grid-cols-2 gap-3">
        <div className="rounded-md border border-teal-300/30 bg-white/10 p-3">
          <RadioTower className="h-6 w-6 text-amber-300" />
          <p className="mt-4 text-sm font-semibold">Live routing</p>
          <div className="mt-3 space-y-2">
            <div className="h-2 rounded-sm bg-teal-300" />
            <div className="h-2 w-3/4 rounded-sm bg-teal-300/60" />
          </div>
        </div>
        <div className="rounded-md border border-amber-300/40 bg-amber-100 p-3 text-amber-950">
          <Database className="h-6 w-6" />
          <p className="mt-4 text-sm font-semibold">Memory bank</p>
          <div className="mt-3 grid grid-cols-3 gap-1">
            {Array.from({ length: 9 }).map((_, index) => (
              <div key={index} className="h-5 rounded-sm bg-amber-300" />
            ))}
          </div>
        </div>
        <div className="col-span-2 rounded-md border border-teal-300/30 bg-teal-950/70 p-3">
          <div className="flex items-center gap-2">
            <GitBranch className="h-5 w-5 text-teal-200" />
            <span className="text-sm font-semibold">Similarity clusters</span>
          </div>
          <div className="mt-4 flex items-center gap-3">
            <div className="h-8 w-16 rounded-md bg-amber-300" />
            <div className="h-1 flex-1 rounded-sm bg-teal-300/50" />
            <div className="h-8 w-16 rounded-md bg-rose-300" />
          </div>
        </div>
      </div>
    </div>
  );
}

