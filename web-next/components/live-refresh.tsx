"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

/** Refresh server data only while the page is visible.  The API shares and
 * throttles upstream FPL reads, so this is safe for the near-live workspace. */
export function LiveRefresh({ everySeconds = 15, active = true }: { everySeconds?: number; active?: boolean }) {
  const router = useRouter();
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => {
      if (document.visibilityState === "visible") router.refresh();
    }, everySeconds * 1000);
    return () => window.clearInterval(timer);
  }, [active, everySeconds, router]);
  return null;
}
