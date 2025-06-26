"use client";

import * as React from "react";
import { useAuthStore } from "@/lib/stores/auth-store";

interface ProtectedRouteProps {
  children: React.ReactNode;
  alternativeContent?: React.ReactNode;
}

export function ProtectedRoute({
  children,
  alternativeContent,
}: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading, checkSession } = useAuthStore();
  const isAuthDisabled = process.env.NEXT_PUBLIC_DISABLE_AUTH === "true";
  const [hasCheckedSession, setHasCheckedSession] = React.useState(false);

  React.useEffect(() => {
    if (!hasCheckedSession) {
      checkSession();
      setHasCheckedSession(true);
    }
  }, [checkSession, hasCheckedSession]);

  // Allow access if auth is disabled
  if (isAuthDisabled) {
    return <>{children}</>;
  }

  // Show loading state
  if (isLoading || !hasCheckedSession) {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <div className="animate-pulse text-lg font-medium">Loading...</div>
      </div>
    );
  }

  // Display alternative content or nothing
  if (!isAuthenticated || !user) {
    return alternativeContent || null;
  }

  return <>{children}</>;
}
