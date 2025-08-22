import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { zitadelClient } from "@/lib/auth/zitadel-client";

const confirmResetSchema = z.object({
  userId: z.string().min(1, "User ID is required"),
  code: z.string().min(1, "Verification code is required"),
  newPassword: z.string().min(8, "Password must be at least 8 characters"),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate input
    const validationResult = confirmResetSchema.safeParse(body);
    if (!validationResult.success) {
      return NextResponse.json(
        { error: "Invalid input", details: validationResult.error.errors },
        { status: 400 }
      );
    }

    const { userId, code, newPassword } = validationResult.data;

    // Reset password with Zitadel
    await zitadelClient.resetPassword(userId, code, newPassword);

    return NextResponse.json({
      success: true,
      message: "Password has been successfully reset.",
    });
  } catch (error) {
    console.error("Password reset confirmation error:", error);

    if (error instanceof Error) {
      // Check for specific Zitadel errors
      if (
        error.message.includes("404") ||
        error.message.includes("not found")
      ) {
        return NextResponse.json(
          { error: "Invalid or expired reset code" },
          { status: 400 }
        );
      }

      if (error.message.includes("400") || error.message.includes("invalid")) {
        return NextResponse.json(
          { error: "Invalid reset code or password requirements not met" },
          { status: 400 }
        );
      }

      if (error.message.includes("expired")) {
        return NextResponse.json(
          {
            error:
              "Reset code has expired. Please request a new password reset.",
          },
          { status: 400 }
        );
      }
    }

    return NextResponse.json(
      { error: "Internal server error" },
      { status: 500 }
    );
  }
}
