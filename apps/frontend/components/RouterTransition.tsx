"use client";

import { useEffect } from "react";
import { usePathname, useSearchParams } from "next/navigation";
import { NavigationProgress, nprogress } from "@mantine/nprogress";

export function RouterTransition() {
  const pathname     = usePathname();
  const searchParams = useSearchParams();

  // Complete the bar whenever the route finishes changing
  useEffect(() => {
    nprogress.complete();
  }, [pathname, searchParams]);

  // Start the bar on any internal-link click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      const anchor = (e.target as HTMLElement).closest("a");
      if (!anchor) return;
      const href = anchor.getAttribute("href");
      // Only same-origin relative paths (skip hash-only, external, etc.)
      if (href && href.startsWith("/") && !href.startsWith("//")) {
        nprogress.start();
      }
    };
    document.addEventListener("click", handleClick);
    return () => document.removeEventListener("click", handleClick);
  }, []);

  return (
    <NavigationProgress
      color="var(--mantine-color-lognis-5)"
      size={3}
      zIndex={9999}
    />
  );
}
