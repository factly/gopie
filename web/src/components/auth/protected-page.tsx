"use client";

import * as React from "react";
import { useSession } from "next-auth/react";
import { redirect } from "next/navigation";

interface ProtectedPageProps {
  children: React.ReactNode;
}

export function ProtectedPage({ children }: ProtectedPageProps) {
  const { status } = useSession();
  const isAuthDisabled = process.env.NEXT_PUBLIC_DISABLE_AUTH === "true";

  // Client-side authentication check
  React.useEffect(() => {
    if (status === "unauthenticated" && !isAuthDisabled) {
      redirect("/api/auth/signin");
    }
  }, [status, isAuthDisabled]);

  // Skip auth entirely if disabled
  if (isAuthDisabled) {
    return <>{children}</>;
  }

  // Show loading state while session is loading
  if (status === "loading") {
    return (
      <div className="flex h-[calc(100vh-4rem)] items-center justify-center">
        <div className="animate-pulse text-lg font-medium">Loading...</div>
      </div>
    );
  }

  // Don't render anything when unauthenticated (will redirect)
  if (status === "unauthenticated") {
    return null;
  }

  // Render children when authenticated
  return <>{children}</>;
}
