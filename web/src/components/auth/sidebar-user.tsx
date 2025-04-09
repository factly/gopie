"use client";

import * as React from "react";
import { useSession, signOut } from "next-auth/react";
import Link from "next/link";
import { LogOut } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { useSidebar } from "@/components/ui/sidebar";

export function SidebarUser() {
  const { data: session, status } = useSession();
  const isLoading = status === "loading";
  const { open: isSidebarOpen } = useSidebar();
  const isAuthDisabled = process.env.NEXT_PUBLIC_DISABLE_AUTH === "true";

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

  // If auth is disabled, show a placeholder user
  if (isAuthDisabled) {
    return (
      <div className="flex h-12 w-full items-center gap-2 px-3 py-2">
        <Avatar className="h-8 w-8">
          <AvatarFallback>AD</AvatarFallback>
        </Avatar>
        {isSidebarOpen && (
          <div className="flex flex-col items-start gap-0.5 overflow-hidden">
            <p className="text-sm font-medium leading-none truncate max-w-[140px]">
              Auth Disabled
            </p>
            <p className="text-xs text-muted-foreground truncate max-w-[140px]">
              Development Mode
            </p>
          </div>
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
      </div>
    );
  }

  if (!session?.user) {
    return (
      <div className="flex items-center px-3 py-2">
        <Button variant="outline" size="sm" asChild className="w-full">
          <Link href="/api/auth/signin">Sign In</Link>
        </Button>
      </div>
    );
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          className="flex h-12 w-full items-center justify-start gap-2 px-3 py-2"
        >
          <Avatar className="h-8 w-8">
            <AvatarImage
              src={session.user.image || ""}
              alt={session.user.name || "User"}
            />
            <AvatarFallback>
              {getInitials(session.user.name || "")}
            </AvatarFallback>
          </Avatar>
          {isSidebarOpen && (
            <div className="flex flex-col items-start gap-0.5 overflow-hidden">
              <p className="text-sm font-medium leading-none truncate max-w-[140px]">
                {session.user.name}
              </p>
              <p className="text-xs text-muted-foreground truncate max-w-[140px]">
                {session.user.email}
              </p>
            </div>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="w-56" align="end" side="top">
        <DropdownMenuLabel className="font-normal">
          <div className="flex flex-col space-y-1">
            <p className="text-sm font-medium leading-none">
              {session.user.name}
            </p>
            <p className="text-xs leading-none text-muted-foreground">
              {session.user.email}
            </p>
          </div>
        </DropdownMenuLabel>
        {/* <DropdownMenuSeparator /> */}
        {/* <DropdownMenuGroup>
          <DropdownMenuItem>
            <User className="mr-2 h-4 w-4" />
            <span>Profile</span>
          </DropdownMenuItem>
          <DropdownMenuItem>
            <Settings className="mr-2 h-4 w-4" />
            <span>Settings</span>
          </DropdownMenuItem>
        </DropdownMenuGroup> */}
        {/* <DropdownMenuSeparator /> */}
        <DropdownMenuItem onClick={handleSignOut}>
          <LogOut className="mr-2 h-4 w-4" />
          <span>Log out</span>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
