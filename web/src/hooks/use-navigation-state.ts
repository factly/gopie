"use client";

import { useEffect, useState, useTransition } from "react";
import { usePathname, useSearchParams } from "next/navigation";

export function useNavigationState() {
  const [isNavigating, setIsNavigating] = useState(false);
  const [isPending, startTransition] = useTransition();
  const pathname = usePathname();
  // Note: This hook should only be used within a Suspense boundary
  // when using useSearchParams()
  const searchParams = useSearchParams();

  useEffect(() => {
    // Set navigating to false when route changes complete
    setIsNavigating(false);
  }, [pathname, searchParams]);

  const startNavigation = () => {
    setIsNavigating(true);
  };

  return {
    isNavigating: isNavigating || isPending,
    startNavigation,
    startTransition,
  };
}