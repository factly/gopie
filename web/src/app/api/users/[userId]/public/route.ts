import { NextRequest, NextResponse } from "next/server";
import { ZitadelClient } from "@/lib/auth/zitadel-client";

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ userId: string }> }
) {
  try {
    const { userId } = await params;

    if (!userId) {
      return NextResponse.json(
        { error: "User ID is required" },
        { status: 400 }
      );
    }

    const zitadelClient = new ZitadelClient();

    // Get public user information from Zitadel
    const publicUserInfo = await zitadelClient.getPublicUserInfo(userId);

    if (!publicUserInfo) {
      return NextResponse.json({ error: "User not found" }, { status: 404 });
    }

    return NextResponse.json({ data: publicUserInfo });
  } catch (error) {
    console.error("Error fetching public user info:", error);
    return NextResponse.json(
      { error: "Failed to fetch user information" },
      { status: 500 }
    );
  }
}
