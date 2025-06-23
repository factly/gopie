"use client";

import * as React from "react";
import { useAuthSession } from "@/hooks/use-auth-session";
import { redirect } from "next/navigation";
import { PageLoading } from "@/components/ui/loading";

interface ProtectedPageProps {
  children: React.ReactNode;
}

export function ProtectedPage({ children }: ProtectedPageProps) {
  const { status, data: session } = useAuthSession();
  const isAuthDisabled = process.env.NEXT_PUBLIC_DISABLE_AUTH === "true";

  // Allow access if auth is disabled
  if (isAuthDisabled) {
    return <>{children}</>;
  }

  // Show loading state
  if (status === "loading") {
    return <PageLoading />;
  }

  // Redirect to login if not authenticated
  if (!session?.user) {
    redirect("/api/auth/signin");
  }

  return <>{children}</>;
}
