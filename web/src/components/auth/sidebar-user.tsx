"use client";

import * as React from "react";
import { signOut } from "next-auth/react";
import Link from "next/link";
import { LogOut } from "lucide-react";

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAuthSession } from "@/hooks/use-auth-session";
import { useSidebar } from "@/components/ui/sidebar";

export function SidebarUser() {
  const { data: session, status } = useAuthSession();
  const isLoading = status === "loading";
  const { open: isSidebarOpen } = useSidebar();
  const isAuthDisabled = process.env.NEXT_PUBLIC_DISABLE_AUTH === "true";
  const user = session?.user;

  const handleSignOut = () => {
    signOut({ callbackUrl: "/" });
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
      <div className="flex items-center px-3 py-2">
        <Avatar className="h-8 w-8">
          <AvatarFallback className="bg-amber-100 text-amber-800">
            AD
          </AvatarFallback>
        </Avatar>
        {isSidebarOpen && (
          <div className="ml-2 text-sm font-medium">Auth Disabled</div>
        )}
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex items-center px-3 py-2">
        <Avatar className="h-8 w-8">
          <AvatarFallback>...</AvatarFallback>
        </Avatar>
        {isSidebarOpen && <div className="ml-2 h-4 w-24 bg-gray-200 rounded" />}
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex items-center px-3 py-2">
        <Button variant="outline" size="sm" asChild>
          <Link href="/api/auth/signin">Sign In</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center px-3 py-2">
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="sm"
            className="relative h-8 w-8 rounded-full mr-0"
          >
            <Avatar className="h-8 w-8">
              <AvatarImage src={user.image || ""} alt={user.name || "User"} />
              <AvatarFallback>{getInitials(user.name || "")}</AvatarFallback>
            </Avatar>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-56" align="end" forceMount>
          <DropdownMenuLabel className="font-normal">
            <div className="flex flex-col space-y-1">
              <p className="text-sm font-medium leading-none">{user.name}</p>
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
      {isSidebarOpen && (
        <div className="ml-2 flex flex-col items-start gap-0.5 overflow-hidden">
          <p className="text-sm font-medium leading-none truncate max-w-[140px]">
            {user.name}
          </p>
          <p className="text-xs text-muted-foreground truncate max-w-[140px]">
            {user.email}
          </p>
        </div>
      )}
    </div>
  );
}
