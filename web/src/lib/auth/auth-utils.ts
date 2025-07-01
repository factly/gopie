import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { zitadelClient, type ZitadelUser } from "./zitadel-client";

const SESSION_COOKIE_NAME = "zitadel-session";
const SESSION_TOKEN_COOKIE_NAME = "zitadel-session-token";

export interface UserSession {
  user: ZitadelUser;
  sessionId: string;
  sessionToken: string;
  accessToken: string;
  expiresAt: number;
}

export async function getSession(): Promise<UserSession | null> {
  const cookieStore = await cookies();
  const sessionId = cookieStore.get(SESSION_COOKIE_NAME)?.value;
  const sessionToken = cookieStore.get(SESSION_TOKEN_COOKIE_NAME)?.value;

  if (!sessionId || !sessionToken) {
    return null;
  }

  try {
    // Verify session is still valid by fetching user info
    const user = await zitadelClient.getUserInfo(sessionId);

    // Get fresh access token
    const tokenResponse = await zitadelClient.getAccessToken();

    return {
      user,
      sessionId,
      sessionToken,
      accessToken: tokenResponse.access_token,
      expiresAt: Date.now() + 24 * 60 * 60 * 1000, // 24 hours
    };
  } catch (error) {
    console.error("Session validation failed:", error);
    // Clear invalid session
    await clearSession();
    return null;
  }
}

export async function createSession(
  sessionId: string,
  sessionToken: string
): Promise<UserSession> {
  const user = await zitadelClient.getUserInfo(sessionId);

  // Get access token for client-side use
  const tokenResponse = await zitadelClient.getAccessToken();

  const cookieStore = await cookies();
  const expiresAt = Date.now() + 24 * 60 * 60 * 1000; // 24 hours

  cookieStore.set(SESSION_COOKIE_NAME, sessionId, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 24 * 60 * 60, // 24 hours in seconds
    path: "/",
  });

  cookieStore.set(SESSION_TOKEN_COOKIE_NAME, sessionToken, {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    maxAge: 24 * 60 * 60, // 24 hours in seconds
    path: "/",
  });

  return {
    user,
    sessionId,
    sessionToken,
    accessToken: tokenResponse.access_token,
    expiresAt,
  };
}

export async function clearSession(): Promise<void> {
  const cookieStore = await cookies();
  const sessionId = cookieStore.get(SESSION_COOKIE_NAME)?.value;

  if (sessionId) {
    try {
      await zitadelClient.deleteSession(sessionId);
    } catch (error) {
      console.error("Failed to delete session from Zitadel:", error);
    }
  }

  cookieStore.delete(SESSION_COOKIE_NAME);
  cookieStore.delete(SESSION_TOKEN_COOKIE_NAME);
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
