import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { zitadelClient } from "@/lib/auth/zitadel-client";
import { cookies } from "next/headers";
import { AUTH_REQUEST_COOKIE, COOKIE_MAX_AGE, SESSION_ID_COOKIE, SESSION_TOKEN_COOKIE } from "@/constants/zitade";

const loginSchema = z.object({
  loginName: z.string().min(1, "Login name is required"),
  password: z.string().min(1, "Password is required"),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate input
    const validationResult = loginSchema.safeParse(body);
    const cookieStore = await cookies();
    const authRequestId = cookieStore.get(AUTH_REQUEST_COOKIE)?.value;
    if (!validationResult.success || !authRequestId) {
      return NextResponse.json(
        { error: "Invalid input", details: validationResult.error?.errors },
        { status: 400 }
      );
    }

    const { loginName, password } = validationResult.data;

    // Step 1: Create session with user check
    const initialSession = await zitadelClient.createSession(loginName);

    cookieStore.set(SESSION_ID_COOKIE, initialSession.sessionId, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax' as const,
      maxAge: COOKIE_MAX_AGE,
      path: '/'
    });

    cookieStore.set(SESSION_TOKEN_COOKIE, initialSession.sessionToken, {
      httpOnly: true,
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'lax' as const,
      maxAge: COOKIE_MAX_AGE,
      path: '/'
    });
    
    // step 2: get session
    const session = await zitadelClient.getSession(initialSession.sessionId);

    if (!session.user) {
      return NextResponse.json(
        { error: "Invalid login credentials" },
        { status: 401 }
      );
    }

    // Step 3: Update session with password
    const authenticatedSession = await zitadelClient.updateSession(
      initialSession.sessionId,
      password
    );
 
     // Check auth Methods
     const authMethods = await zitadelClient.getAuthMethods(
      session.user.id,
      authenticatedSession.sessionToken
    );
    
    const data ={
      isMFAEnabled: false,
      userId: session.user.id,
      callbackUrl: ""
    }

    if (
      authMethods.authMethodTypes?.includes("AUTHENTICATION_METHOD_TYPE_TOTP")
    ) {
      data.isMFAEnabled = true;
    } else {

    // Step 4: Finalize auth request 
    const authRequestResponse = await zitadelClient.finalizeAuthRequest(
      authRequestId,
      authenticatedSession.sessionId,
      authenticatedSession.sessionToken
    );
    data.callbackUrl = authRequestResponse.callbackUrl;
    }

    return NextResponse.json({
      success: true,
      ...data,
    });
  } catch (error) {
    console.error("Login error:", error);

    if (error instanceof Error) {
      // Check for specific Zitadel errors and pass through detailed messages
      if (
        error.message.includes("404") ||
        error.message.includes("not found")
      ) {
        // If it's our enhanced error message about email login, pass it through
        if (error.message.includes("Email login failed")) {
          return NextResponse.json({ error: error.message }, { status: 401 });
        }

        return NextResponse.json(
          { error: "Invalid login credentials" },
          { status: 401 }
        );
      }

      if (error.message.includes("401") || error.message.includes("invalid")) {
        return NextResponse.json(
          { error: "Invalid login credentials" },
          { status: 401 }
        );
      }

      if (error.message.includes("403")) {
        return NextResponse.json(
          { error: "Access denied" },
          { status: 403 }
        );
      }
    }

    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
