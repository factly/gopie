import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { zitadelClient } from "@/lib/auth/zitadel-client";
import { cookies } from "next/headers";
import { COOKIE_MAX_AGE, SESSION_ID_COOKIE, SESSION_TOKEN_COOKIE } from "@/constants/zitade";

const loginSchema = z.object({
  userId: z.string().min(1, "user id is required"),
  email: z.string().email("Invalid email address"),
  password: z.string().min(1, "Password is required"),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate input
    const validationResult = loginSchema.safeParse(body);

    console.log({validationResult});
    
    if (!validationResult.success) {
      return NextResponse.json(
        { error: "Invalid input", details: validationResult.error?.errors },
        { status: 400 }
      );
    }

    const { userId, email, password } = validationResult.data;

    console.log({userId, email, password});

    // step 1: create session
    const session = await zitadelClient.createSession(email);
    if (!session) {
      return NextResponse.json(
        { error: "Failed to create session" },
        { status: 401 }
      );
    }

    console.log({session});

    // Step 2: Update session with password
    const authenticatedSession = await zitadelClient.updateSession(
      session.sessionId,
      password
    );

    console.log({authenticatedSession});

    // Step 3: validate TOTP
    const resp = await zitadelClient.startTOTPRegistration(userId, authenticatedSession.sessionToken);
    if (!resp) {
      return NextResponse.json(
        { error: "Failed to start TOTP registration" },
        { status: 401 }
      );
    }


    const cookieStore = await cookies();
    cookieStore.set(SESSION_ID_COOKIE, session.sessionId, {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      maxAge: COOKIE_MAX_AGE // 7 days
    });
    cookieStore.set(SESSION_TOKEN_COOKIE, authenticatedSession.sessionToken, {
      httpOnly: true,
      sameSite: "lax",
      secure: process.env.NODE_ENV === "production",
      maxAge: COOKIE_MAX_AGE // 7 days
    });
  
    return NextResponse.json({
      success: true,
      uri: resp.uri,
      secret: resp.secret
    });

  } catch (error) {
    console.error("Login error:", error);

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
