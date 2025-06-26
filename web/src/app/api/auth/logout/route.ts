import { NextResponse } from "next/server";
import { clearSession } from "@/lib/auth/auth-utils";

export async function POST() {
  try {
    await clearSession();

    return NextResponse.json({
      success: true,
      message: "Logged out successfully",
    });
  } catch (error) {
    console.error("Logout error:", error);

    return NextResponse.json({ error: "Failed to logout" }, { status: 500 });
  }
}
