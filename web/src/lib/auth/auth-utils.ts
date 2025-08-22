import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { zitadelClient, type ZitadelUser } from "./zitadel-client";
import {
  SESSION_ID_COOKIE,
  ACCESS_TOKEN_COOKIE,
  SESSION_TOKEN_COOKIE,
} from "@/constants/zitade";

export interface UserSession {
  user: ZitadelUser;
  accessToken: string;
  expiresAt: number;
}

export async function getSession(): Promise<UserSession | null> {
  const cookieStore = await cookies();
  const accessToken = cookieStore.get(ACCESS_TOKEN_COOKIE)?.value;

  if (!accessToken) {
    return null;
  }

  try {
    // Verify session is still valid by fetching user info
    const user = await zitadelClient.getUserInfo(accessToken);

    return {
      user,
      accessToken,
      expiresAt: Date.now() + 24 * 60 * 60 * 1000, // 24 hours
    };
  } catch (error) {
    console.error("Failed to get session from Zitadel:", error);
    // Clear invalid session
    await clearSession();
    return null;
  }
}

export async function clearSession(): Promise<void> {
  const cookieStore = await cookies();
  const sessionId = cookieStore.get(SESSION_ID_COOKIE)?.value;

  if (sessionId) {
    try {
      await zitadelClient.deleteSession(sessionId);
    } catch (error) {
      console.error("Failed to delete session from Zitadel:", error);
    }
  }

  cookieStore.delete(SESSION_ID_COOKIE);
  cookieStore.delete(SESSION_TOKEN_COOKIE);
  cookieStore.delete(ACCESS_TOKEN_COOKIE);
}

export async function requireAuth(): Promise<UserSession> {
  const session = await getSession();

  if (!session) {
    redirect("/auth/login");
  }

  return session;
}

export async function redirectIfAuthenticated(fallbackPath: string = "/") {
  const session = await getSession();

  if (session) {
    redirect(fallbackPath);
  }
}
