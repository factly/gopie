"use client";

import * as React from "react";
import { UserDropdown } from "@/components/auth/user-dropdown";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuthSession } from "@/hooks/use-auth-session";

interface AuthStatusProps {
  showName?: boolean;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function AuthStatus({
  showName = true,
  size = "md",
  className = "",
}: AuthStatusProps) {
  const { data: session, status } = useAuthSession();
  const isLoading = status === "loading";
  const user = session?.user;
  const isAuthDisabled = process.env.NEXT_PUBLIC_DISABLE_AUTH === "true";

  // If auth is disabled, show a disabled auth indicator
  if (isAuthDisabled) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <div className="px-3 py-1 text-xs bg-amber-100 text-amber-800 ">
          Auth Disabled
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <Skeleton className="h-8 w-8 rounded-full" />
        {showName && <Skeleton className="h-4 w-24" />}
      </div>
    );
  }

  if (!user) {
    return (
      <div className={`flex items-center gap-2 ${className}`}>
        <Button
          variant="outline"
          size={size === "lg" ? "default" : "sm"}
          asChild
          className={className}
        >
          <Link href="/api/auth/signin">Sign In</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {showName && (
        <span className="text-sm font-medium hidden sm:inline-block">
          {user.name}
        </span>
      )}
      <UserDropdown />
    </div>
  );
}
