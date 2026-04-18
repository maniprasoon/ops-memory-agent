"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

const routes = ["/dashboard", "/chat", "/timeline"];

export function RoutePreloader() {
  const router = useRouter();

  useEffect(() => {
    const timeout = window.setTimeout(() => {
      routes.forEach((route) => router.prefetch(route));
    }, 250);

    return () => window.clearTimeout(timeout);
  }, [router]);

  return null;
}

