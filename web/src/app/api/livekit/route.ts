import { AccessToken, TrackSource } from "livekit-server-sdk";
import { env } from "@/lib/env";
import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  // Get datasetId from query parameter
  const { searchParams } = new URL(request.url);
  const datasetId = searchParams.get("datasetId");

  if (!datasetId) {
    return NextResponse.json(
      { error: "Missing datasetId parameter" },
      { status: 400 }
    );
  }

  try {
    // Create a new AccessToken
    const token = new AccessToken(env.LIVEKIT_API_KEY, env.LIVEKIT_API_SECRET, {
      identity: datasetId,
      name: `dataset-${datasetId}`,
      ttl: 3600 * 24, // 24 hour token
    });

    // Create room name based on datasetId
    const roomName = `dataset-${datasetId}`;

    // Grant all required permissions with more explicit settings
    token.addGrant({
      room: roomName,
      roomJoin: true,
      canPublish: true,
      canPublishData: true,
      canSubscribe: true,
      canPublishSources: [TrackSource.MICROPHONE],
      roomCreate: true,
      roomAdmin: false,
      roomList: false,
      canUpdateOwnMetadata: true,
    });

    // Return the token as a JSON response
    return NextResponse.json({
      token: await token.toJwt(),
      serverUrl: env.NEXT_PUBLIC_LIVEKIT_URL,
    });
  } catch (error) {
    console.error("Error generating LiveKit token:", error);
    return NextResponse.json(
      { error: "Failed to generate token" },
      { status: 500 }
    );
  }
}
