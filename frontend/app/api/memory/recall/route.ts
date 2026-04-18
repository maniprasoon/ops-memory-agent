import { NextResponse } from "next/server";

const backendUrl = "http://127.0.0.1:8000";

export async function POST(request: Request) {
  const body = await request.json();
  const response = await fetch(`${backendUrl}/api/memory/recall`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store"
  });

  const data = await response.json();
  return NextResponse.json(data, { status: response.status });
}

