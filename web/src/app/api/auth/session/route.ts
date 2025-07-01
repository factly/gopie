import { NextResponse } from "next/server";
import { getSession } from "@/lib/auth/auth-utils";

export async function GET() {
  try {
    const session = await getSession();

    if (!session) {
      return NextResponse.json({ authenticated: false }, { status: 401 });
    }

    return NextResponse.json({
      authenticated: true,
      user: session.user,
      accessToken: session.accessToken,
      expiresAt: session.expiresAt,
    });
  } catch (error) {
    console.error("Session check error:", error);

    return NextResponse.json(
      { authenticated: false, error: "Failed to check session" },
      { status: 500 }
    );
  }
}
