import { NextRequest, NextResponse } from "next/server";
import { z } from "zod";
import { zitadelClient } from "@/lib/auth/zitadel-client";

const registerSchema = z.object({
  username: z.string().min(3, "Username must be at least 3 characters"),
  email: z.string().email("Invalid email address"),
  firstName: z.string().min(1, "First name is required"),
  lastName: z.string().min(1, "Last name is required"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    // Validate input
    const validationResult = registerSchema.safeParse(body);
    if (!validationResult.success) {
      return NextResponse.json(
        { error: "Invalid input", details: validationResult.error.errors },
        { status: 400 }
      );
    }

    const userData = validationResult.data;

    // Register user with Zitadel
    const result = await zitadelClient.registerUser(userData);

    return NextResponse.json({
      success: true,
      userId: result.userId,
      message: "User registered successfully",
    });
  } catch (error) {
    console.error("Registration error:", error);

    if (error instanceof Error) {
      // Check for specific Zitadel errors
      if (
        error.message.includes("already exists") ||
        error.message.includes("409")
      ) {
        return NextResponse.json(
          { error: "User already exists" },
          { status: 409 }
        );
      }

      if (error.message.includes("400")) {
        return NextResponse.json(
          { error: "Invalid user data" },
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
