import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { zitadelClient } from "@/lib/auth/zitadel-client";

const resetPasswordSchema = z.object({
  email: z.string().email("Invalid email address"),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate input
    const validationResult = resetPasswordSchema.safeParse(body);
    if (!validationResult.success) {
      return NextResponse.json(
        {
          error: "Invalid email address",
          details: validationResult.error.errors,
        },
        { status: 400 }
      );
    }

    const { email } = validationResult.data;

    // Request password reset from Zitadel
    await zitadelClient.requestPasswordReset(email);

    return NextResponse.json({
      success: true,
      message:
        "If an account with that email exists, you will receive a password reset link shortly.",
    });
  } catch (error) {
    console.error("Password reset error:", error);

    if (error instanceof Error) {
      // Check for specific Zitadel errors
      if (
        error.message.includes("404") ||
        error.message.includes("not found")
      ) {
        // Still return success for security reasons (don't reveal if user exists)
        return NextResponse.json({
          success: true,
          message:
            "If an account with that email exists, you will receive a password reset link shortly.",
        });
      }

      if (error.message.includes("400")) {
        return NextResponse.json({ error: "Invalid request" }, { status: 400 });
      }
    }

    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
