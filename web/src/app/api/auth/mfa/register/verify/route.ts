import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { zitadelClient } from "@/lib/auth/zitadel-client";
import { cookies } from "next/headers";
import { AUTH_REQUEST_COOKIE, SESSION_ID_COOKIE, SESSION_TOKEN_COOKIE } from "@/constants/zitade";

const loginSchema = z.object({
  userId: z.string().min(1, "user id is required"),
  code: z.string().min(1, "code is required"),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate input
    const validationResult = loginSchema.safeParse(body);
    const cookieStore = await cookies();
    const sessionToken = cookieStore.get(SESSION_TOKEN_COOKIE)?.value;
    const authRequest = cookieStore.get(AUTH_REQUEST_COOKIE)?.value;
    const sessionId = cookieStore.get(SESSION_ID_COOKIE)?.value;
    
    if (!validationResult.success || !sessionToken || !authRequest || !sessionId) {
      return NextResponse.json(
        { error: "Invalid input", details: validationResult.error?.errors },
        { status: 400 }
      );
    }

    const { userId, code } = validationResult.data;

    // Step 1: validate TOTP
    const resp = await zitadelClient.verifyTOTPRegistration(userId, sessionToken, code);
    if (!resp) {
      return NextResponse.json(
        { error: "Failed to start TOTP registration" },
        { status: 401 }
      );
    }

    // Step 2: final auth request
    const finalAuthRequest = await zitadelClient.finalizeAuthRequest(authRequest,sessionId, sessionToken);
    if (!finalAuthRequest) {
      return NextResponse.json(
        { error: "Failed to finalize auth request" },
        { status: 401 }
      );
    }
    
    return NextResponse.json({
      success: true,
    });

  } catch (error) {
    if (error instanceof Error) {
      // Check for specific Zitadel errors and pass through detailed messages
      if (
        error.message.includes("404") ||
        error.message.includes("not found")
      ) {
        return NextResponse.json(
          { error: "Failed to start TOTP registration" },
          { status: 401 }
        );
      }

      if (error.message.includes("401") || error.message.includes("invalid")) {
        return NextResponse.json(
          { error: "Failed to start TOTP registration" },
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
