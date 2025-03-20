"use client";

import * as React from "react";
import { useSession } from "next-auth/react";
import { UserDropdown } from "@/components/auth/user-dropdown";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Skeleton } from "@/components/ui/skeleton";

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
  const { data: session, status } = useSession();
  const isLoading = status === "loading";
  const user = session?.user;

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
