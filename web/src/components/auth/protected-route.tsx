"use client";

import * as React from "react";
import { useSession } from "next-auth/react";
import { useRouter, usePathname } from "next/navigation";
import { Skeleton } from "@/components/ui/skeleton";

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { status } = useSession();
  const router = useRouter();
  const pathname = usePathname();
  const isLoading = status === "loading";
  const isAuthenticated = status === "authenticated";
  const isAuthDisabled = process.env.NEXT_PUBLIC_DISABLE_AUTH === "true";

  React.useEffect(() => {
    // Skip authentication check if auth is disabled
    if (isAuthDisabled) return;

    // Check if the user is not authenticated and not on the auth pages
    if (!isLoading && !isAuthenticated) {
      // Redirect to sign-in page with return URL
      const returnUrl = encodeURIComponent(pathname);
      router.push(`/api/auth/signin?callbackUrl=${returnUrl}`);
    }
  }, [isLoading, isAuthenticated, router, pathname, isAuthDisabled]);

  // If auth is disabled, render children immediately
  if (isAuthDisabled) {
    return <>{children}</>;
  }

  if (isLoading) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Skeleton className="h-12 w-12 rounded-full" />
          <Skeleton className="h-4 w-40" />
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
