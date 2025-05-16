"use client";

import { useEffect } from "react";
import { useSession, signOut } from "next-auth/react";
import { type Session } from "next-auth";

/**
 * Enhanced version of useSession that handles refresh token errors
 * by automatically signing out the user
 */
export function useAuthSession() {
  const session = useSession();

  useEffect(() => {
    // Check if there's a token error and sign out if needed
    const error = (session.data as Session & { error?: string })?.error;

    if (error === "RefreshAccessTokenError") {
      // Sign out the user when a refresh token error occurs
      console.log("Auth session expired, signing out...");
      signOut({ callbackUrl: "/api/auth/signin" });
    }
  }, [session.data]);

  return session;
}
