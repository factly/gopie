import {
  AUTH_REQUEST_COOKIE,
  COOKIE_MAX_AGE,
  PKCE_STATE_COOKIE,
  PKCE_VERIFIER_COOKIE,
} from "@/constants/zitade";
import { zitadelClient } from "@/lib/auth/zitadel-client";
import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  try {
    // Check if we have an existing valid auth request in cookies
    const existingAuthRequestId = req.cookies.get(AUTH_REQUEST_COOKIE)?.value;
    const existingPkceVerifier = req.cookies.get(PKCE_VERIFIER_COOKIE)?.value;
    const existingState = req.cookies.get(PKCE_STATE_COOKIE)?.value;

    // If we have existing auth request data, validate it first
    if (existingAuthRequestId && existingPkceVerifier && existingState) {
      try {
        const authRequest = await zitadelClient.getAuthRequest(
          existingAuthRequestId
        );

        // Check if auth request is still valid and not used (within 5 minutes of creation)
        const authRequestAge =
          Date.now() - new Date(authRequest.creationDate).getTime();
        const pkceVerifierAge =
          Date.now() - new Date(existingPkceVerifier).getTime();
        const stateAge = Date.now() - new Date(existingState).getTime();
        const fiveMinutesInMs = 5 * 60 * 1000;

        // check ages of auth request and pkce verifier and state
        if (
          authRequestAge < fiveMinutesInMs &&
          pkceVerifierAge < fiveMinutesInMs &&
          stateAge < fiveMinutesInMs
        ) {
          // Reuse existing valid auth request
          return NextResponse.json({
            authRequestId: existingAuthRequestId,
            reused: true,
          });
        }
      } catch (error) {
        // Auth request is invalid, continue to create new one
        console.log("Existing auth request invalid, creating new one");
      }
    }

    // Generate code verifier parameters
    const codeVerifierParams = await zitadelClient.generateCodeVerifier();

    // Make OAuth request with code verifier parameters
    const redirectUrl: string = await zitadelClient.makeOAuthRequest(
      "/oauth/v2/authorize",
      codeVerifierParams
    );

    if (redirectUrl) {
      // Extract auth request ID from the redirect URL
      const url = new URL(redirectUrl);
      const authRequestId =
        url.searchParams.get("authRequest") || url.pathname.split("/").pop();

      if (!authRequestId) {
        return NextResponse.json(
          { error: "Failed to extract auth request ID" },
          { status: 500 }
        );
      }

      // Set cookies with 10-minute expiry
      const cookieOptions = {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "lax" as const,
        maxAge: COOKIE_MAX_AGE,
        path: "/",
      };

      const response = NextResponse.json({
        authRequestId,
      });

      response.cookies.set(AUTH_REQUEST_COOKIE, authRequestId, cookieOptions);
      response.cookies.set(
        PKCE_VERIFIER_COOKIE,
        codeVerifierParams.codeVerifier,
        cookieOptions
      );
      response.cookies.set(
        PKCE_STATE_COOKIE,
        codeVerifierParams.state,
        cookieOptions
      );

      return response;
    }

    return NextResponse.json(
      { error: "OAuth initiation failed" },
      { status: 500 }
    );
  } catch (error) {
    if (error instanceof Error) {
      if (error.message.includes("403")) {
        return NextResponse.json({ error: "Access denied" }, { status: 403 });
      }
    }
    // console.error("OAuth error:", error);
    return NextResponse.json(
      { error: "Internal Server Error" },
      { status: 500 }
    );
  }
}

// Helper function to clear auth cookies
export function clearAuthCookies(response: NextResponse) {
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
