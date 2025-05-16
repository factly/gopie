"use client";

import * as React from "react";
import { useAuthSession } from "@/hooks/use-auth-session";

interface ProtectedRouteProps {
  children: React.ReactNode;
  alternativeContent?: React.ReactNode;
}

export function ProtectedRoute({
  children,
  alternativeContent,
}: ProtectedRouteProps) {
  const { status, data: session } = useAuthSession();
  const isAuthDisabled = process.env.NEXT_PUBLIC_DISABLE_AUTH === "true";

  // Allow access if auth is disabled
  if (isAuthDisabled) {
    return <>{children}</>;
  }

  // Show loading state
  if (status === "loading") {
    return (
      <div className="flex h-full w-full items-center justify-center">
        <div className="animate-pulse text-lg font-medium">Loading...</div>
      </div>
    );
  }

  // Display alternative content or nothing
  if (!session?.user) {
    return alternativeContent || null;
  }

  return <>{children}</>;
}
