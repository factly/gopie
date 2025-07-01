"use client";

import * as React from "react";
import Link from "next/link";
import { LogOut } from "lucide-react";
import { useRouter } from "next/navigation";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuthStore } from "@/lib/stores/auth-store";
import { cn } from "@/lib/utils";

export function SidebarUser() {
  const router = useRouter();
  const { user, isAuthenticated, isLoading, logout } = useAuthStore();
  const isAuthDisabled = process.env.NEXT_PUBLIC_DISABLE_AUTH === "true";

  const handleSignOut = async () => {
    await logout();
    router.push("/auth/login");
  };

  const getInitials = (name: string) => {
    if (!name) return "U";
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase()
      .substring(0, 2);
  };

  // If auth is disabled, show a disabled auth indicator
  if (isAuthDisabled) {
    return (
      <div className={cn("flex items-center", "px-3 py-2")}>
        <Avatar className="h-8 w-8">
          <AvatarFallback className="bg-amber-100 text-amber-800">
            AD
          </AvatarFallback>
        </Avatar>
        <div className="ml-2 text-sm font-medium">Auth Disabled</div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className={cn("flex items-center", "px-3 py-2")}>
        <Avatar className="h-8 w-8">
          <AvatarFallback>...</AvatarFallback>
        </Avatar>
        <div className="ml-2 h-4 w-24 bg-gray-200 rounded" />
      </div>
    );
  }

  if (!isAuthenticated || !user) {
    return (
      <div className={cn("flex items-center", "px-3 py-2")}>
        <Button variant="outline" size="sm" asChild>
          <Link href="/auth/login">Sign In</Link>
        </Button>
        <Button variant="ghost" size="icon" className="h-8 w-8" asChild>
          <Link href="/auth/login">
            <Avatar className="h-8 w-8">
              <AvatarFallback>SI</AvatarFallback>
            </Avatar>
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className={cn("flex items-center", "px-3 py-2")}>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="relative h-8 w-8 rounded-full mr-0"
          >
            <Avatar className="h-8 w-8">
              <AvatarImage
                src={user.profilePicture || ""}
                alt={user.displayName || "User"}
              />
              <AvatarFallback>
                {getInitials(user.displayName || "")}
              </AvatarFallback>
            </Avatar>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-56" align="end" forceMount>
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              <p className="text-sm font-medium leading-none">
                {user.displayName}
              </p>
              <p className="text-xs leading-none text-muted-foreground">
                {user.email}
              </p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuItem onClick={handleSignOut}>
            <LogOut className="mr-2 h-4 w-4" />
            <span>Log out</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <div className="ml-2 flex flex-col items-start gap-0.5 overflow-hidden">
        <p className="text-sm font-medium leading-none truncate max-w-[140px]">
          {user.displayName}
        </p>
        <p className="text-xs text-muted-foreground truncate max-w-[140px]">
          {user.email}
        </p>
      </div>
    </div>
  );
}
