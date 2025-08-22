import { NextRequest, NextResponse } from "next/server";
import { ZitadelClient } from "@/lib/auth/zitadel-client";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { successUrl, failureUrl } = body;

    if (!successUrl || !failureUrl) {
      return NextResponse.json(
        { error: "Success URL and failure URL are required" },
        { status: 400 }
      );
    }

    const zitadelClient = new ZitadelClient();
    const { authUrl } = await zitadelClient.initiateOAuth(
      successUrl,
      failureUrl
    );

    return NextResponse.json({ authUrl });
  } catch (error) {
    console.error("OAuth initiation error:", error);
    return NextResponse.json(
      { error: "Failed to initiate OAuth flow" },
      { status: 500 }
    );
  }
}
