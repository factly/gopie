import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { zitadelClient } from "@/lib/auth/zitadel-client";
import { createSession } from "@/lib/auth/auth-utils";

const loginSchema = z.object({
  loginName: z.string().min(1, "Login name is required"),
  password: z.string().min(1, "Password is required"),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate input
    const validationResult = loginSchema.safeParse(body);
    if (!validationResult.success) {
      return NextResponse.json(
        { error: "Invalid input", details: validationResult.error.errors },
        { status: 400 }
      );
    }

    const { loginName, password } = validationResult.data;

    // Step 1: Create session with user check
    const initialSession = await zitadelClient.createSession(loginName);

    // Step 2: Update session with password
    const authenticatedSession = await zitadelClient.updateSession(
      initialSession.sessionId,
      password
    );

    // Step 3: Create session cookies
    const userSession = await createSession(
      authenticatedSession.sessionId,
      authenticatedSession.sessionToken
    );

    return NextResponse.json({
      success: true,
      user: userSession.user,
      accessToken: userSession.accessToken,
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
