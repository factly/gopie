"use client";

import * as React from "react";
import { useAuthStore } from "@/lib/stores/auth-store";
import { redirect } from "next/navigation";
import { PageLoading } from "@/components/ui/loading";

interface ProtectedPageProps {
  children: React.ReactNode;
}

export function ProtectedPage({ children }: ProtectedPageProps) {
  const { isAuthenticated, isLoading, user, checkSession } = useAuthStore();
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

  // Show loading state while checking session
  if (isLoading || !hasCheckedSession) {
    return <PageLoading />;
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated || !user) {
    redirect("/auth/login");
  }

  return <>{children}</>;
}
