import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { zitadelClient } from "@/lib/auth/zitadel-client";
import { cookies } from "next/headers";
import { AUTH_REQUEST_COOKIE, SESSION_ID_COOKIE, SESSION_TOKEN_COOKIE } from "@/constants/zitade";

const loginSchema = z.object({
  code: z.string().min(1, "Login name is required"),
  userId: z.string().min(1, "User ID is required"),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate input
    const validationResult = loginSchema.safeParse(body);
    const cookieStore = await cookies();
    const authRequestId = cookieStore.get(AUTH_REQUEST_COOKIE)?.value;
    const sessionId = cookieStore.get(SESSION_ID_COOKIE)?.value;
    const sessionToken = cookieStore.get(SESSION_TOKEN_COOKIE)?.value;
    
    if (!validationResult.success || !authRequestId || !sessionId || !sessionToken) {
      return NextResponse.json(
        { error: "Invalid input", details: validationResult.error?.errors },
        { status: 400 }
      );
    }

    const { code, userId } = validationResult.data;

    // Step 1: validate TOTP
    const resp = await zitadelClient.verifyTOTPRegistration(userId, sessionToken, code);
    if (!resp) {
      return NextResponse.json(
        { error: "Invalid TOTP code" },
        { status: 401 }
      );
    }
  
    // Step 2: Finalize auth request 
    const authRequestResponse = await zitadelClient.finalizeAuthRequest(
      authRequestId,
      sessionId,
      sessionToken
    );

    return NextResponse.json({
      success: true,
      callbackUrl: authRequestResponse.callbackUrl,
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
    }

    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
