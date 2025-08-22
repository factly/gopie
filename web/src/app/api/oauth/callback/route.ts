import { NextRequest, NextResponse } from "next/server";
import { zitadelClient } from "@/lib/auth/zitadel-client";
import {
  PKCE_STATE_COOKIE,
  PKCE_VERIFIER_COOKIE,
  ACCESS_TOKEN_COOKIE,
  SESSION_ID_COOKIE,
  SESSION_TOKEN_COOKIE,
  AUTH_REQUEST_COOKIE,
} from "@/constants/zitade";
import { cookies } from "next/headers";

export async function GET(req: NextRequest) {
  const baseUrl = process.env.NEXT_PUBLIC_APP_URL;

  try {
    const { searchParams } = new URL(req.url);
    const authorizationCode = searchParams.get("code");
    const state = searchParams.get("state");
    const error = searchParams.get("error");

    // Handle OAuth errors
    if (error) {
      console.error("OAuth error:", error);
      const loginUrl = new URL("/auth/login?error=oauth_failed", baseUrl);
      return NextResponse.redirect(loginUrl);
    }

    // Validate required parameters
    if (!authorizationCode) {
      console.error("Missing authorization code");
      const loginUrl = new URL(
        "/auth/login?error=missing_oauth_params",
        baseUrl
      );
      return NextResponse.redirect(loginUrl);
    }

    // Get PKCE parameters from cookies
    const codeVerifier = req.cookies.get(PKCE_VERIFIER_COOKIE)?.value;
    const storedState = req.cookies.get(PKCE_STATE_COOKIE)?.value;

    if (!codeVerifier) {
      console.error("Missing code verifier in cookies");
      const loginUrl = new URL(
        "/auth/login?error=missing_oauth_params",
        baseUrl
      );
      return NextResponse.redirect(loginUrl);
    }

    // Validate state parameter (CSRF protection)
    if (state !== storedState) {
      console.error("State parameter mismatch");
      const loginUrl = new URL(
        "/auth/login?error=oauth_callback_failed",
        baseUrl
      );
      return NextResponse.redirect(loginUrl);
    }

    // Exchange authorization code for access token using PKCE
    const tokenResponse = await zitadelClient.getAccessToken(
      authorizationCode,
      codeVerifier
    );

    // Get user info from the access token
    // Note: You may need to implement a method to get user info from the token
    // For now, we'll redirect to a success page or dashboard

    // Clear auth cookies since we've completed the flow
    const response = NextResponse.redirect(new URL("/", baseUrl));
    clearAuthCookies(response);

    // Set session cookies with the new tokens
    const cookieOptions = {
      httpOnly: true,
      secure: process.env.NODE_ENV === "production",
      sameSite: "lax" as const,
      maxAge: tokenResponse.expires_in || 3600, // Use token expiry or default to 1 hour
      path: "/",
    };

    const cookieStore = await cookies();

    const sessionId = cookieStore.get(SESSION_ID_COOKIE);
    const sessionToken = cookieStore.get(SESSION_TOKEN_COOKIE);

    if (sessionId) {
      cookieStore.set(SESSION_ID_COOKIE, sessionId.value, {
        ...cookieOptions,
        maxAge: tokenResponse.expires_in || 3600,
      });
    }

    if (sessionToken) {
      cookieStore.set(SESSION_TOKEN_COOKIE, sessionToken.value, {
        ...cookieOptions,
        maxAge: tokenResponse.expires_in || 3600,
      });
    }

    // Set access token cookie
    cookieStore.set(
      ACCESS_TOKEN_COOKIE,
      tokenResponse.access_token,
      cookieOptions
    );

    return response;
  } catch (error) {
    console.error("OAuth callback error:", error);
    const loginUrl = new URL(
      "/auth/login?error=oauth_callback_failed",
      baseUrl
    );
    return NextResponse.redirect(loginUrl);
  }
}

// Helper function to clear auth cookies
function clearAuthCookies(response: NextResponse) {
  const cookieOptions = {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    maxAge: 0,
    path: "/",
  };

  response.cookies.set(AUTH_REQUEST_COOKIE, "", cookieOptions);
  response.cookies.set(PKCE_VERIFIER_COOKIE, "", cookieOptions);
  response.cookies.set(PKCE_STATE_COOKIE, "", cookieOptions);
}
